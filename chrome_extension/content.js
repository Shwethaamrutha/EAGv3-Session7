// Floating + button on every page
const btn = document.createElement("div");
btn.id = "rag-index-btn";
btn.innerHTML = "+";
btn.title = "Add this page to RAG knowledge base";
document.body.appendChild(btn);

let isIndexing = false;

btn.addEventListener("click", async () => {
  if (isIndexing) return;
  isIndexing = true;
  btn.innerHTML = "...";
  btn.classList.add("indexing");

  // Extract page content
  let content = document.body.innerText;
  const url = window.location.href;

  // For PDF pages or pages with very little text, send URL for server-side extraction
  const isPdf = url.endsWith(".pdf") || document.contentType === "application/pdf";
  if (isPdf || content.trim().length < 200) {
    content = "__FETCH_URL__";
  }

  const data = {
    url: url,
    title: document.title || url.split("/").pop(),
    content: content.substring(0, 50000),
  };

  const result = await chrome.runtime.sendMessage({ type: "INDEX_PAGE", data });

  if (result && !result.error) {
    btn.innerHTML = "✓";
    btn.classList.remove("indexing");
    btn.classList.add("done");
    setTimeout(() => {
      btn.innerHTML = "+";
      btn.classList.remove("done");
      isIndexing = false;
    }, 2000);
  } else {
    btn.innerHTML = "!";
    btn.classList.remove("indexing");
    btn.classList.add("error");
    btn.title = result ? result.error : "Failed to connect";
    setTimeout(() => {
      btn.innerHTML = "+";
      btn.classList.remove("error");
      btn.title = "Add this page to RAG knowledge base";
      isIndexing = false;
    }, 3000);
  }
});
