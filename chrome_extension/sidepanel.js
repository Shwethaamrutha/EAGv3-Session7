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

function addMessage(role, text, sources) {
  // Remove empty state
  const empty = chat.querySelector(".empty-state");
  if (empty) empty.remove();

  const msg = document.createElement("div");
  msg.className = `msg ${role}`;

  if (role === "bot" && typeof marked !== "undefined") {
    msg.innerHTML = marked.parse(text);
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
  const query = input.value.trim();
  if (!query || isQuerying) return;

  isQuerying = true;
  sendBtn.disabled = true;
  input.value = "";

  addMessage("user", query);
  addMessage("bot", "Searching knowledge base...");

  const result = await chrome.runtime.sendMessage({ type: "QUERY", query });

  // Remove "searching" message
  chat.lastChild.remove();

  if (result.error) {
    addMessage("bot", "Error: " + result.error);
  } else {
    addMessage("bot", result.answer, result.sources);
  }

  isQuerying = false;
  sendBtn.disabled = false;
}

sendBtn.addEventListener("click", sendQuery);
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendQuery();
});

// Load pages on open
loadPages();

// Listen for updates
chrome.storage.onChanged.addListener((changes) => {
  if (changes.indexed_pages) loadPages();
});
