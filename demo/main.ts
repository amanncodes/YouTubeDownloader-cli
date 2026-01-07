const btn = document.getElementById("download")!;
const output = document.getElementById("output") as HTMLPreElement;

btn.addEventListener("click", async () => {
  output.textContent = "Downloading…";

  const urlInput = document.getElementById("url") as HTMLInputElement;
  const fileInput = document.getElementById("file") as HTMLInputElement;

  const form = new FormData();

  if (fileInput.files && fileInput.files.length > 0) {
    form.append("file", fileInput.files[0]);
  } else if (urlInput.value.trim()) {
    form.append("url", urlInput.value.trim());
  } else {
    output.textContent = "Please provide a URL or JSON file.";
    return;
  }

  try {
    const res = await fetch("/download", {
      method: "POST",
      body: form,
    });

    const data = await res.json();

    if (!res.ok) {
      output.textContent = "Error:\n" + data.error;
    } else {
      output.textContent = data.output;
    }
  } catch (err) {
    output.textContent = "Request failed";
  }
});
