const resumeText = document.getElementById("resumeText");
const geminiApiKey = document.getElementById("geminiApiKey");
const useGemini = document.getElementById("useGemini");
const analyzeBtn = document.getElementById("analyzeBtn");
const statusEl = document.getElementById("status");
const jobOutput = document.getElementById("jobOutput");
const matchedSkillsEl = document.getElementById("matchedSkills");
const missingSkillsEl = document.getElementById("missingSkills");
const categoryBucketsEl = document.getElementById("categoryBuckets");
const priorityListEl = document.getElementById("priorityList");
const roadmapListEl = document.getElementById("roadmapList");

function getGeminiKeyFromEnv() {
  if (typeof GEMINI_API_KEY_FROM_ENV === "undefined") return "";
  return String(GEMINI_API_KEY_FROM_ENV).trim();
}

function effectiveGeminiApiKey() {
  return getGeminiKeyFromEnv() || geminiApiKey.value.trim();
}

function renderSimpleList(element, items, emptyText = "None") {
  element.innerHTML = "";

  if (!items || items.length === 0) {
    const li = document.createElement("li");
    li.textContent = emptyText;
    element.appendChild(li);
    return;
  }

  items.forEach(item => {
    const li = document.createElement("li");
    li.textContent = item;
    element.appendChild(li);
  });
}

function renderMatched(element, items) {
  element.innerHTML = "";

  if (!items || items.length === 0) {
    const li = document.createElement("li");
    li.textContent = "No matched technical skills found.";
    element.appendChild(li);
    return;
  }

  items.forEach(item => {
    const li = document.createElement("li");
    li.textContent = item.skill;
    element.appendChild(li);
  });
}

function renderMissing(element, items) {
  element.innerHTML = "";

  if (!items || items.length === 0) {
    const li = document.createElement("li");
    li.textContent = "No missing technical skills found.";
    element.appendChild(li);
    return;
  }

  items.forEach(item => {
    const li = document.createElement("li");
    li.innerHTML = `${item.skill} <span class="pill">${item.priority}</span>`;
    element.appendChild(li);
  });
}

function renderCategoryBuckets(grouped) {
  categoryBucketsEl.innerHTML = "";

  const categories = Object.keys(grouped || {});
  if (categories.length === 0) {
    categoryBucketsEl.textContent = "No missing skills grouped yet.";
    return;
  }

  categories.forEach(category => {
    const block = document.createElement("div");
    block.className = "category-block";

    const title = document.createElement("div");
    title.className = "category-title";
    title.textContent = category.replaceAll("_", " ");

    const list = document.createElement("div");
    list.textContent = grouped[category].join(", ");

    block.appendChild(title);
    block.appendChild(list);
    categoryBucketsEl.appendChild(block);
  });
}

function renderPriorityList(items) {
  priorityListEl.innerHTML = "";

  if (!items || items.length === 0) {
    const li = document.createElement("li");
    li.textContent = "No priority recommendations yet.";
    priorityListEl.appendChild(li);
    return;
  }

  items.forEach(item => {
    const li = document.createElement("li");
    li.textContent = `${item.skill} — ${item.priority} (mentioned ${item.count} time(s))`;
    priorityListEl.appendChild(li);
  });
}

function renderRoadmap(items) {
  roadmapListEl.innerHTML = "";

  if (!items || items.length === 0) {
    const li = document.createElement("li");
    li.textContent = "No roadmap generated yet.";
    roadmapListEl.appendChild(li);
    return;
  }

  items.forEach(item => {
    const li = document.createElement("li");
    li.textContent = `${item.week}: ${item.focus}`;
    roadmapListEl.appendChild(li);
  });
}

document.addEventListener("DOMContentLoaded", async () => {
  const result = await chrome.storage.local.get(["resumeText", "geminiApiKey", "useGemini"]);
  if (result.resumeText) {
    resumeText.value = result.resumeText;
  }
  if (result.geminiApiKey) {
    geminiApiKey.value = result.geminiApiKey;
  }
  if (typeof result.useGemini === "boolean") {
    useGemini.checked = result.useGemini;
  }
});

analyzeBtn.addEventListener("click", async () => {
  const resume = resumeText.value.trim();

  if (!resume) {
    statusEl.textContent = "Please paste your skills/resume first.";
    return;
  }

  const apiKey = effectiveGeminiApiKey();
  const geminiOn = useGemini.checked;

  await chrome.storage.local.set({
    resumeText: resume,
    geminiApiKey: geminiApiKey.value.trim(),
    useGemini: geminiOn
  });

  if (geminiOn && !apiKey) {
    statusEl.textContent =
      "Set GEMINI_API_KEY in job-gap-coach-ver-2/.env, run node scripts/write-env-config.cjs, reload the extension — or paste a key above.";
    return;
  }

  statusEl.textContent = "Reading current job page...";
  analyzeBtn.disabled = true;

  chrome.runtime.sendMessage({ type: "GET_JOB_PAGE_DATA" }, async (response) => {
    try {
      if (!response || !response.success) {
        statusEl.textContent = response?.error || "Something went wrong.";
        return;
      }

      const data = response.data;
      const fullJobText = `${data.title}\n${data.company}\n${data.description}`;

      let comparison;
      if (geminiOn) {
        statusEl.textContent = "Analyzing with Gemini (gemini-3-flash-preview)...";
        try {
          comparison = await analyzeJobGapWithGemini(apiKey, resume, data);
        } catch (err) {
          statusEl.textContent = err?.message || "Gemini request failed.";
          return;
        }
      } else {
        comparison = compareSkills(resume, fullJobText);
      }

      renderMatched(matchedSkillsEl, comparison.matched);
      renderMissing(missingSkillsEl, comparison.missing);
      renderCategoryBuckets(comparison.groupedMissing);
      renderPriorityList(comparison.missing);
      renderRoadmap(comparison.roadmap);

      statusEl.textContent =
        `Found ${comparison.matched.length} matched skill(s) and ${comparison.missing.length} missing skill(s).` +
        (geminiOn ? " (Gemini)" : " (local dictionary)");

      const previewText = (data.description || "No text found.").slice(0, 12000);

      jobOutput.textContent =
        `Title: ${data.title || "N/A"}\n\n` +
        `Company: ${data.company || "N/A"}\n\n` +
        `URL: ${data.url || "N/A"}\n\n` +
        `Description Preview:\n${previewText}`;
    } finally {
      analyzeBtn.disabled = false;
    }
  });
});