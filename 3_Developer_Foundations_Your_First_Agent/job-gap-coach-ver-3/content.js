function getText(el) {
  return el?.innerText?.trim() || el?.textContent?.trim() || "";
}

function textFromSelectors(selectors) {
  for (const selector of selectors) {
    const el = document.querySelector(selector);
    const text = getText(el);
    if (text) return text;
  }
  return "";
}

function extractJobDescriptionNow() {
  const descriptionSelectors = [
    ".jobs-description",
    ".jobs-box__html-content",
    ".jobs-description-content__text",
    ".jobs-search__job-details--container",
    ".show-more-less-html__markup",
    ".jobs-description__content",
    "[class*='jobs-description']",
    "[class*='job-description']",
    "main"
  ];

  const text = textFromSelectors(descriptionSelectors);

  if (text && text.length > 500) return text;

  return getText(document.body) || "";
}

async function extractJobPageData() {
  const tryExtract = () => {
    const title =
      textFromSelectors([
        ".job-details-jobs-unified-top-card__job-title",
        ".t-24.job-details-jobs-unified-top-card__job-title",
        "h1",
        "[class*='job-title']"
      ]) || document.title;

    const company = textFromSelectors([
      ".job-details-jobs-unified-top-card__company-name",
      ".jobs-unified-top-card__company-name",
      "[class*='company-name']",
      "[class*='company'] a",
      "[data-test='company-name']"
    ]);

    const description = extractJobDescriptionNow();

    return {
      title,
      company,
      description,
      url: window.location.href
    };
  };

  let result = tryExtract();

  if (!result.description || result.description.length < 500) {
    await new Promise(resolve => setTimeout(resolve, 1200));
    result = tryExtract();
  }

  if (!result.description || result.description.length < 500) {
    await new Promise(resolve => setTimeout(resolve, 1800));
    result = tryExtract();
  }

  return result;
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "EXTRACT_JOB_PAGE") {
    extractJobPageData().then(sendResponse);
    return true;
  }
});