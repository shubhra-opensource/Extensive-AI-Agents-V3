chrome.runtime.onInstalled.addListener(() => {
    chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true });
  });
  
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === "GET_JOB_PAGE_DATA") {
      chrome.tabs.query({ active: true, currentWindow: true }, async (tabs) => {
        const activeTab = tabs[0];
  
        if (!activeTab || !activeTab.id) {
          sendResponse({ success: false, error: "No active tab found." });
          return;
        }
  
        try {
          const response = await chrome.tabs.sendMessage(activeTab.id, {
            type: "EXTRACT_JOB_PAGE"
          });
          sendResponse({ success: true, data: response });
        } catch (error) {
          sendResponse({
            success: false,
            error: "Could not read this page. Try opening a normal job page and refresh it once."
          });
        }
      });
  
      return true;
    }
  });