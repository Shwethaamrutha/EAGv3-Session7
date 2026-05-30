const API_BASE = "http://localhost:8080";

chrome.action.onClicked.addListener(async (tab) => {
  chrome.sidePanel.open({ windowId: tab.windowId });
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "INDEX_PAGE") {
    indexPage(message.data).then(sendResponse);
    return true;
  }
  if (message.type === "QUERY") {
    queryKnowledge(message.query).then(sendResponse);
    return true;
  }
  if (message.type === "GET_PAGES") {
    getIndexedPages().then(sendResponse);
    return true;
  }
});

async function indexPage(data) {
  try {
    const resp = await fetch(`${API_BASE}/index`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url: data.url,
        title: data.title,
        content: data.content,
      }),
    });
    const result = await resp.json();
    // Store in local list
    const pages = (await chrome.storage.local.get("indexed_pages")).indexed_pages || [];
    pages.push({ url: data.url, title: data.title, chunks: result.chunks, timestamp: Date.now() });
    await chrome.storage.local.set({ indexed_pages: pages });
    return result;
  } catch (e) {
    return { error: e.message };
  }
}

async function queryKnowledge(query) {
  try {
    const resp = await fetch(`${API_BASE}/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });
    return await resp.json();
  } catch (e) {
    return { error: e.message };
  }
}

async function getIndexedPages() {
  const pages = (await chrome.storage.local.get("indexed_pages")).indexed_pages || [];
  return { pages };
}
