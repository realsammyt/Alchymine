"use strict";

const crypto = require("crypto");
const express = require("express");
const puppeteer = require("puppeteer-core");

const app = express();
const PORT = process.env.PDF_PORT || 3001;

// Require a shared secret token for all non-health requests.
// The API service must set the same PDF_SERVICE_TOKEN in its environment
// and pass it as "Authorization: Bearer <token>" on every request.
const PDF_SERVICE_TOKEN = process.env.PDF_SERVICE_TOKEN;
if (!PDF_SERVICE_TOKEN) {
  console.error("FATAL: PDF_SERVICE_TOKEN environment variable is not set.");
  process.exit(1);
}

function requireBearerToken(req, res, next) {
  const authHeader = req.headers["authorization"] || "";
  const [scheme, token] = authHeader.split(" ");
  if (scheme !== "Bearer") {
    return res.status(401).json({ error: "Unauthorized" });
  }
  const tokenBuffer = Buffer.from(token || "");
  const expectedBuffer = Buffer.from(PDF_SERVICE_TOKEN || "");
  if (
    tokenBuffer.length !== expectedBuffer.length ||
    !crypto.timingSafeEqual(tokenBuffer, expectedBuffer)
  ) {
    return res.status(401).json({ error: "Unauthorized" });
  }
  next();
}

app.use(express.json({ limit: "10mb" }));

let browser;

async function getBrowser() {
  if (!browser || !browser.isConnected()) {
    browser = await puppeteer.launch({
      executablePath:
        process.env.PUPPETEER_EXECUTABLE_PATH || "/usr/bin/chromium",
      headless: true,
      args: [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--single-process",
      ],
    });
  }
  return browser;
}

// Health check endpoint
app.get("/health", (_req, res) => {
  res.json({ status: "ok", service: "alchymine-pdf" });
});

// PDF generation endpoint — requires valid bearer token
app.post("/generate", requireBearerToken, async (req, res) => {
  let page;
  try {
    const { html, options = {} } = req.body;

    if (!html) {
      return res.status(400).json({ error: "html field is required" });
    }

    const b = await getBrowser();
    page = await b.newPage();

    await page.setJavaScriptEnabled(false);
    await page.setContent(html, {
      waitUntil: "networkidle0",
      timeout: 30000,
    });

    const pdf = await page.pdf({
      format: options.format || "A4",
      margin: options.margin || {
        top: "1cm",
        right: "1cm",
        bottom: "1cm",
        left: "1cm",
      },
      printBackground: true,
      ...options,
    });

    res.set({
      "Content-Type": "application/pdf",
      "Content-Length": pdf.length,
    });
    res.send(pdf);
  } catch (err) {
    console.error("PDF generation error:", err);
    res.status(500).json({ error: "PDF generation failed" });
  } finally {
    if (page) {
      await page.close().catch(() => {});
    }
  }
});

// Start server
app.listen(PORT, "0.0.0.0", () => {
  console.log(`Alchymine PDF service listening on port ${PORT}`);
});

// Graceful shutdown
process.on("SIGTERM", async () => {
  console.log("SIGTERM received, shutting down...");
  if (browser) {
    await browser.close();
  }
  process.exit(0);
});

process.on("SIGINT", async () => {
  console.log("SIGINT received, shutting down...");
  if (browser) {
    await browser.close();
  }
  process.exit(0);
});
