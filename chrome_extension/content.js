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
  const content = document.body.innerText;
  const data = {
    url: window.location.href,
    title: document.title,
    content: content.substring(0, 50000), // Cap at 50K chars
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
