/**
 * Chat transport: the SSE parser.
 *
 * Issue #278. A `data:` field ends at the first newline, so the server
 * splits a newline-bearing chunk across several `data:` lines inside one
 * event. The parser has to accumulate those lines and join them back
 * with a newline at the blank line that ends the event; a parser that
 * yields per line drops everything after the first newline of a chunk,
 * which is every paragraph break the model writes.
 *
 * These drive `streamChat` directly with a scripted byte stream, so the
 * assertions are about the parser rather than about the hook above it.
 */

import { ChatError, streamChat } from "../chat";

/**
 * A `Response` whose body reads back *frames* in order, one network read
 * per entry. Splitting a frame across entries is how a test says "this
 * arrived in two TCP reads".
 */
function sseResponse(frames: string[]): Response {
  const encoder = new TextEncoder();
  const queue = [...frames];
  const reader = {
    read: async () => {
      if (queue.length === 0) return { done: true, value: undefined };
      return { done: false, value: encoder.encode(queue.shift() as string) };
    },
    releaseLock: () => {},
  };
  return {
    ok: true,
    status: 200,
    body: { getReader: () => reader },
  } as unknown as Response;
}

async function collect(frames: string[]): Promise<string[]> {
  global.fetch = jest.fn().mockResolvedValue(sseResponse(frames));
  const chunks: string[] = [];
  for await (const chunk of streamChat({ message: "hi", system_key: null })) {
    chunks.push(chunk);
  }
  return chunks;
}

afterEach(() => {
  jest.restoreAllMocks();
});

describe("streamChat framing", () => {
  it("joins the data lines of one event with a newline", async () => {
    expect(await collect(["data: A\ndata: B\n\n"])).toEqual(["A\nB"]);
  });

  it("leaves a single-line event exactly as it was", async () => {
    expect(await collect(["data: Hello\n\n"])).toEqual(["Hello"]);
  });

  it("keeps an empty data line, so a trailing newline survives", async () => {
    // The server frames the chunk "text\n" as two data lines, the second
    // of them empty. Dropping it would eat the line break.
    expect(await collect(["data: text\ndata: \n\n"])).toEqual(["text\n"]);
  });

  it("keeps a blank line between paragraphs", async () => {
    const wire = "data: One.\ndata: \ndata: Two.\n\n";

    expect(await collect([wire])).toEqual(["One.\n\nTwo."]);
  });

  it("keeps a leading newline", async () => {
    expect(await collect(["data: \ndata: indented\n\n"])).toEqual(["\nindented"]);
  });

  it("yields one string per event, in order", async () => {
    const wire = "data: first\n\ndata: second\ndata: third\n\n";

    expect(await collect([wire])).toEqual(["first", "second\nthird"]);
  });

  it("reassembles a frame split across network reads", async () => {
    expect(await collect(["data: A\nda", "ta: B\n", "\n"])).toEqual(["A\nB"]);
  });

  it("handles a frame split mid-word", async () => {
    expect(await collect(["data: Par", "agraph\ndata: two\n\n"])).toEqual(["Paragraph\ntwo"]);
  });

  it("tolerates CRLF line endings", async () => {
    expect(await collect(["data: A\r\ndata: B\r\n\r\n"])).toEqual(["A\nB"]);
  });

  it("skips an event that carries no data lines", async () => {
    expect(await collect([": keep-alive\n\ndata: real\n\n"])).toEqual(["real"]);
  });

  it("skips an event whose only data line is empty", async () => {
    expect(await collect(["data: \n\ndata: real\n\n"])).toEqual(["real"]);
  });

  it("delivers a frame that lost its terminator to a closed connection", async () => {
    // Not a spec discard: the text in a complete data line is real, and
    // dropping it would lose the tail of a reply without saying so.
    expect(await collect(["data: A\ndata: B\n"])).toEqual(["A\nB"]);
  });
});

describe("streamChat control frames", () => {
  it("stops at the done sentinel", async () => {
    const wire = "data: before\n\nevent: done\ndata: \n\ndata: after\n\n";

    expect(await collect([wire])).toEqual(["before"]);
  });

  it("stops at a done sentinel with no data line", async () => {
    expect(await collect(["data: before\n\nevent: done\n\n"])).toEqual(["before"]);
  });

  it("throws the message of an error frame", async () => {
    global.fetch = jest
      .fn()
      .mockResolvedValue(sseResponse(["event: error\ndata: Streaming failed\n\n"]));

    const error = (await streamChat({ message: "hi", system_key: null })
      .next()
      .catch((e) => e)) as ChatError;

    expect(error).toBeInstanceOf(ChatError);
    expect(error.message).toBe("Streaming failed");
  });

  it("keeps every line of a multi-line error message", async () => {
    global.fetch = jest
      .fn()
      .mockResolvedValue(sseResponse(["event: error\ndata: One.\ndata: Two.\n\n"]));

    const error = (await streamChat({ message: "hi", system_key: null })
      .next()
      .catch((e) => e)) as ChatError;

    expect(error.message).toBe("One.\nTwo.");
  });

  it("yields what arrived before an error frame, then throws", async () => {
    global.fetch = jest
      .fn()
      .mockResolvedValue(sseResponse(["data: partial\n\nevent: error\ndata: Streaming failed\n\n"]));

    const chunks: string[] = [];
    let thrown: unknown = null;
    try {
      for await (const chunk of streamChat({ message: "hi", system_key: null })) {
        chunks.push(chunk);
      }
    } catch (e) {
      thrown = e;
    }

    expect(chunks).toEqual(["partial"]);
    expect(thrown).toBeInstanceOf(ChatError);
  });

  it("falls back to a message when an error frame carries no text", async () => {
    global.fetch = jest.fn().mockResolvedValue(sseResponse(["event: error\ndata: \n\n"]));

    const error = (await streamChat({ message: "hi", system_key: null })
      .next()
      .catch((e) => e)) as ChatError;

    expect(error).toBeInstanceOf(ChatError);
    expect(error.message.length).toBeGreaterThan(0);
  });

  it("scopes an event name to its own event", async () => {
    // A name must not leak past the blank line, or the frame after a
    // named one would be read as more of it.
    const wire = "event: ping\ndata: x\n\ndata: y\n\n";

    expect(await collect([wire])).toEqual(["x", "y"]);
  });
});
