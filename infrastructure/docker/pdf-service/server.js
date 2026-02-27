"use strict";

const express = require("express");
const puppeteer = require("puppeteer-core");

const app = express();
const PORT = process.env.PDF_PORT || 3001;

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

// PDF generation endpoint
app.post("/generate", async (req, res) => {
  let page;
  try {
    const { html, options = {} } = req.body;

    if (!html) {
      return res.status(400).json({ error: "html field is required" });
    }

    const b = await getBrowser();
    page = await b.newPage();

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
    res.status(500).json({ error: err.message });
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
