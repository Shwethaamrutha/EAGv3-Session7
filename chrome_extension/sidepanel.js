const chat = document.getElementById("chat");
const input = document.getElementById("input");
const sendBtn = document.getElementById("send");
const pagesBar = document.getElementById("pages-bar");
const pageCount = document.getElementById("page-count");

let isQuerying = false;

async function loadPages() {
  const result = await chrome.runtime.sendMessage({ type: "GET_PAGES" });
  const pages = result.pages || [];
  pageCount.textContent = `${pages.length} pages indexed`;
  pagesBar.innerHTML = "";
  for (const p of pages.slice(-10)) {
    const chip = document.createElement("div");
    chip.className = "page-chip";
    chip.textContent = p.title || p.url;
    chip.title = p.url;
    pagesBar.appendChild(chip);
  }
}

function renderLatex(el) {
  if (typeof katex === "undefined") return;
  // Block math: $$...$$
  el.innerHTML = el.innerHTML.replace(/\$\$([\s\S]*?)\$\$/g, (match, tex) => {
    try {
      return katex.renderToString(tex.trim(), { displayMode: true, throwOnError: false });
    } catch { return match; }
  });
  // Inline math: $...$
  el.innerHTML = el.innerHTML.replace(/\$([^\$\n]+?)\$/g, (match, tex) => {
    try {
      return katex.renderToString(tex.trim(), { displayMode: false, throwOnError: false });
    } catch { return match; }
  });
}

function addMessage(role, text, sources) {
  // Remove empty state
  const empty = chat.querySelector(".empty-state");
  if (empty) empty.remove();

  const msg = document.createElement("div");
  msg.className = `msg ${role}`;

  if (role === "bot" && typeof marked !== "undefined") {
    msg.innerHTML = marked.parse(text);
    renderLatex(msg);
  } else {
    msg.textContent = text;
  }

  if (sources && sources.length > 0) {
    const srcDiv = document.createElement("div");
    srcDiv.className = "sources";
    srcDiv.textContent = "Sources: " + sources.map(s => s.split("/").pop()).join(", ");
    msg.appendChild(srcDiv);
  }

  chat.appendChild(msg);
  chat.scrollTop = chat.scrollHeight;
}

async function sendQuery() {
  const query = input.value.replace(/\s+/g, ' ').trim();
  if (!query || isQuerying) return;

  if (query === "/clear") {
    input.value = "";
    await clearState();
    return;
  }

  if (query === "/new") {
    input.value = "";
    try {
      const r = await fetch("http://localhost:8080/new", { method: "POST" });
      const data = await r.json();
      const empty2 = chat.querySelector(".empty-state");
      if (empty2) empty2.remove();
      addMessage("bot", `New session. FAISS index persisted: ${data.persisted_chunks} chunks available.`);
    } catch (e) {
      addMessage("bot", "Error: " + e.message);
    }
    return;
  }

  if (query.startsWith("/remove ")) {
    const source = query.slice(8).trim();
    input.value = "";
    try {
      const r = await fetch("http://localhost:8080/remove", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: source }),
      });
      const data = await r.json();
      const empty2 = chat.querySelector(".empty-state");
      if (empty2) empty2.remove();
      if (data.status === "removed") {
        addMessage("bot", `Removed ${data.removed} chunks matching "${source}". ${data.remaining} items remaining.`);
      } else {
        addMessage("bot", `No chunks found matching "${source}".`);
      }
      loadPages();
    } catch (e) {
      addMessage("bot", "Error: " + e.message);
    }
    return;
  }

  isQuerying = true;
  sendBtn.disabled = true;
  input.value = "";

  addMessage("user", query);

  // Remove empty state
  const empty = chat.querySelector(".empty-state");
  if (empty) empty.remove();

  // Create log container (appears first)
  const logContainer = document.createElement("div");
  logContainer.className = "query-log-container";
  chat.appendChild(logContainer);

  // Create answer message (appears after logs)
  const msg = document.createElement("div");
  msg.className = "msg bot";
  msg.innerHTML = "<em>Thinking...</em>";
  chat.appendChild(msg);
  chat.scrollTop = chat.scrollHeight;

  try {
    const resp = await fetch("http://localhost:8080/agent", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let fullText = "";
    let sources = [];
    let started = false;
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop(); // keep incomplete last line in buffer
      for (const line of lines) {
        if (line.startsWith("data: ")) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.type === "token") {
              if (!started) { msg.innerHTML = ""; started = true; }
              fullText += data.text;
              msg.innerHTML = typeof marked !== "undefined" ? marked.parse(fullText) : fullText;
              renderLatex(msg);
              chat.scrollTop = chat.scrollHeight;
            } else if (data.type === "sources") {
              sources = data.sources;
            } else if (data.type === "step") {
              const stepDiv = document.createElement("div");
              stepDiv.className = "step-log";
              stepDiv.innerHTML = `<span class="step-name">[${data.step}]</span> ${data.detail}`;
              logContainer.appendChild(stepDiv);
              chat.scrollTop = chat.scrollHeight;
            } else if (data.type === "retrieval") {
              const logDiv = document.createElement("div");
              logDiv.className = "retrieval-log";
              let logHtml = `<div class="log-header">Retrieved ${data.hits} chunks</div>`;
              logHtml += `<div class="log-sources">Sources: ${data.sources.map(s => s.split("/").pop()).join(", ")}</div>`;
              for (const c of data.chunks.slice(0, 4)) {
                logHtml += `<div class="log-chunk"><span class="log-src">[${c.source} #${c.chunk_index}]</span> ${c.chunk.slice(0, 100)}...</div>`;
              }
              logDiv.innerHTML = logHtml;
              logContainer.appendChild(logDiv);
              chat.scrollTop = chat.scrollHeight;
            }
          } catch (e) { /* skip malformed lines */ }
        }
      }
    }

    // Add sources footer
    if (sources.length > 0) {
      const srcDiv = document.createElement("div");
      srcDiv.className = "sources";
      srcDiv.textContent = "Sources: " + sources.map(s => s.split("/").pop()).join(", ");
      msg.appendChild(srcDiv);
    }
  } catch (e) {
    msg.innerHTML = "Error: " + e.message;
  }

  isQuerying = false;
  sendBtn.disabled = false;
}

sendBtn.addEventListener("click", sendQuery);
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendQuery();
});

async function clearState() {
  try {
    await fetch("http://localhost:8080/clear", { method: "POST" });
    await chrome.storage.local.set({ indexed_pages: [] });
    chat.innerHTML = '<div class="empty-state">State cleared. Click <b>+</b> on pages to index them.</div>';
    loadPages();
  } catch (e) {
    addMessage("bot", "Error clearing: " + e.message);
  }
}

// Load pages on open
loadPages();

// Listen for updates
chrome.storage.onChanged.addListener((changes) => {
  if (changes.indexed_pages) loadPages();
});
