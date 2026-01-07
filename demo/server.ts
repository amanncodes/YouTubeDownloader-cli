import express from "express";
import multer from "multer";
import { spawn } from "child_process";
import path from "path";
import fs from "fs";

const app = express();
const upload = multer({ dest: "uploads/" });

app.use(express.json());
app.use(express.static("."));

app.post("/download", upload.single("file"), (req, res) => {
  const url = req.body.url;
  const file = req.file;

  let arg: string;

  if (file) {
    arg = file.path;
  } else if (url) {
    arg = url;
  } else {
    return res.status(400).json({ error: "No input provided" });
  }

  const python = spawn("python", ["../ytcli.py", arg]);

  let output = "";
  let error = "";

  python.stdout.on("data", (data) => {
    output += data.toString();
  });

  python.stderr.on("data", (data) => {
    error += data.toString();
  });

  python.on("close", (code) => {
    if (file) fs.unlinkSync(file.path);

    if (code === 0) {
      res.json({ status: "success", output });
    } else {
      res.status(500).json({ status: "error", error: error || output });
    }
  });
});

app.listen(3000, () => {
  console.log("Demo server running on http://localhost:3000");
});
