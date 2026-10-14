// JobPulse Web Application Core Controller

let currentMatches = [];
let currentProfile = null;
let activeStage = "all";
let activeSkillFilters = new Set();
let spotlightIndex = 0;

const POPULAR_SKILLS = [
  "Python", "FastAPI", "React", "Next.js", "Docker", "Kubernetes", 
  "AWS", "PostgreSQL", "Redis", "TypeScript", "JavaScript"
];

// Initialize on DOM Ready
document.addEventListener("DOMContentLoaded", () => {
  setupEventListeners();
  updateLiveDate();
  renderSkillFilterChips();
  loadProfileAndData();
});

function updateLiveDate() {
  const el = document.getElementById("liveDate");
  if (el) {
    const now = new Date();
    const options = { weekday: 'short', day: 'numeric', month: 'short' };
    el.textContent = now.toLocaleDateString('en-US', options);
  }
}

function setupEventListeners() {
  // Theme Toggle
  const themeBtn = document.getElementById("themeToggleBtn");
  if (themeBtn) {
    themeBtn.addEventListener("click", () => {
      const current = document.documentElement.getAttribute("data-theme") || "dark";
      const next = current === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      themeBtn.innerHTML = next === "dark" ? "&#9790;" : "&#9788;";
    });
  }

  // Keyboard shortcut Ctrl/Cmd + K for Command Palette
  window.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      openModal("searchPaletteModal");
      document.getElementById("paletteInput")?.focus();
    }
    if (e.key === "Escape") {
      closeAllModals();
      closeDrawer();
      closeSampleMenu();
    }
  });

  // Close sample menu when clicking outside
  document.addEventListener("click", (e) => {
    if (!e.target.closest(".sample-profiles-dropdown")) {
      closeSampleMenu();
    }
  });

  // Search Palette Input
  const paletteInput = document.getElementById("paletteInput");
  if (paletteInput) {
    paletteInput.addEventListener("input", (e) => {
      renderPaletteResults(e.target.value);
    });
  }

  // Inline Search Input with real-time filtering
  const inlineSearch = document.getElementById("inlineSearch");
  if (inlineSearch) {
    inlineSearch.addEventListener("input", () => {
      applyFilters();
    });
  }

  // Resume Dropzone
  const dropzone = document.getElementById("resumeDropzone");
  const fileInput = document.getElementById("resumeFileInput");
  if (dropzone && fileInput) {
    dropzone.addEventListener("click", () => fileInput.click());
    dropzone.addEventListener("dragover", (e) => {
      e.preventDefault();
      dropzone.classList.add("dragover");
    });
    dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
    dropzone.addEventListener("drop", (e) => {
      e.preventDefault();
      dropzone.classList.remove("dragover");
      if (e.dataTransfer.files.length > 0) {
        handleResumeUpload(e.dataTransfer.files[0]);
      }
    });
    fileInput.addEventListener("change", (e) => {
      if (e.target.files.length > 0) {
        handleResumeUpload(e.target.files[0]);
      }
    });
  }
}

async function loadProfileAndData() {
  try {
    const [profileRes, summaryRes, feedRes] = await Promise.all([
      fetch("/api/profile"),
      fetch("/api/pipeline/summary"),
      fetch("/api/jobs/feed?limit=100")
    ]);

    currentProfile = await profileRes.json();
    const summary = await summaryRes.json();
    currentMatches = await feedRes.json();

    // If matches are empty, trigger initial seed sync automatically
    if (!currentMatches || currentMatches.length === 0) {
      await syncJobs(false);
      return;
    }

    renderProfileHeader();
    renderResumeBanner();
    renderPipelineSummary(summary);
    renderSpotlightCard();
    renderQuickFeed();
    applyFilters();
  } catch (err) {
    console.error("Error loading dashboard data:", err);
  }
}

function renderProfileHeader() {
  if (!currentProfile) return;
  const avatarEl = document.getElementById("userAvatar");
  if (avatarEl) {
    const initials = currentProfile.full_name
      .split(" ")
      .map(n => n[0])
      .join("")
      .substring(0, 2)
      .toUpperCase();
    avatarEl.textContent = initials || "CA";
  }
}

function renderResumeBanner() {
  if (!currentProfile) return;
  
  const nameEl = document.getElementById("bannerCandidateName");
  const seniorityEl = document.getElementById("bannerSeniority");
  const expEl = document.getElementById("bannerExp");
  const headlineEl = document.getElementById("bannerHeadline");
  const avatarEl = document.getElementById("bannerAvatar");
  const skillsListEl = document.getElementById("bannerSkillsList");

  if (nameEl) nameEl.textContent = currentProfile.full_name;
  if (seniorityEl) seniorityEl.textContent = currentProfile.seniority || "Senior";
  if (expEl) expEl.textContent = `${currentProfile.years_of_experience || 5} Years Exp`;
  if (headlineEl) headlineEl.textContent = `${currentProfile.title} • Target: ${currentProfile.target_roles.join(", ")}`;
  
  if (avatarEl) {
    const initials = currentProfile.full_name
      .split(" ")
      .map(n => n[0])
      .join("")
      .substring(0, 2)
      .toUpperCase();
    avatarEl.textContent = initials;
  }

  // Render Interactive Skill Chips
  if (skillsListEl) {
    skillsListEl.innerHTML = (currentProfile.skills || []).map(skill => `
      <span class="interactive-skill-tag">
        ${escapeHtml(skill)}
        <span class="remove-skill-x" title="Remove skill" onclick="removeSkill('${escapeHtml(skill)}')">&times;</span>
      </span>
    `).join("");
  }

  // Update default email input in digest modal
  const digestEmail = document.getElementById("digestEmailInput");
  if (digestEmail && currentProfile.email) {
    digestEmail.value = currentProfile.email;
  }
}

async function promptAddSkill() {
  const skill = prompt("Enter a skill or technology to add to your resume profile (e.g. Docker, AWS, React, Python):");
  if (!skill || !skill.trim()) return;

  try {
    const res = await fetch(`/api/profile/skills/add?skill=${encodeURIComponent(skill.trim())}`, { method: "POST" });
    if (res.ok) {
      currentProfile = await res.json();
      await loadProfileAndData();
      showToast(`Added '${skill.trim()}' to your profile! Match scores updated.`);
    }
  } catch (err) {
    console.error("Failed to add skill:", err);
  }
}

async function removeSkill(skill) {
  try {
    const res = await fetch(`/api/profile/skills/remove?skill=${encodeURIComponent(skill)}`, { method: "DELETE" });
    if (res.ok) {
      currentProfile = await res.json();
      await loadProfileAndData();
      showToast(`Removed '${skill}'. Matches recalculated.`);
    }
  } catch (err) {
    console.error("Failed to remove skill:", err);
  }
}

function renderSkillFilterChips() {
  const container = document.getElementById("skillFilterChips");
  if (!container) return;

  container.innerHTML = POPULAR_SKILLS.map(skill => `
    <button class="skill-chip-filter ${activeSkillFilters.has(skill.toLowerCase()) ? 'active' : ''}" 
            onclick="toggleSkillFilter('${skill}')">
      ${escapeHtml(skill)}
    </button>
  `).join("");
}

function toggleSkillFilter(skill) {
  const s = skill.toLowerCase();
  if (activeSkillFilters.has(s)) {
    activeSkillFilters.delete(s);
  } else {
    activeSkillFilters.add(s);
  }
  renderSkillFilterChips();
  applyFilters();
}

function renderPipelineSummary(summary) {
  if (!summary) return;
  
  const mainMetric = document.getElementById("heroMainMetric");
  if (mainMetric) {
    mainMetric.innerHTML = `${summary.total_scanned_jobs} <span>Active Opportunities</span>`;
  }
  
  const avgScoreEl = document.getElementById("heroAvgScore");
  if (avgScoreEl) avgScoreEl.textContent = `${summary.avg_match_score}%`;
  
  const matchedCountEl = document.getElementById("heroMatchedCount");
  if (matchedCountEl) matchedCountEl.textContent = summary.matched_count;

  // Dynamically compute top ceiling salary from active inventory
  let maxSalary = 0;
  if (currentMatches && currentMatches.length > 0) {
    currentMatches.forEach(m => {
      const nums = (m.job.salary_range || "").replace(/,/g, "").match(/\d{5,6}/g);
      if (nums) {
        nums.forEach(n => {
          const val = parseInt(n, 10);
          if (val > maxSalary && val < 600000) maxSalary = val;
        });
      }
    });
  }
  const ceilingEl = document.getElementById("topCeilingSalary");
  if (ceilingEl) {
    ceilingEl.textContent = maxSalary > 0 ? `$${maxSalary.toLocaleString()}` : "$180,000+";
  }

  // Pipeline Funnel Bars strictly dynamic from SQLite database
  const funnelContainer = document.getElementById("pipelineFunnel");
  if (funnelContainer) {
    const totalCount = summary.total_scanned_jobs || 1;
    const stages = [
      { key: "all", label: "Discovered", count: summary.total_scanned_jobs, dot: "dot-blue", max: totalCount },
      { key: "matched", label: "Matched", count: summary.matched_count, dot: "dot-purple", max: totalCount },
      { key: "saved", label: "Saved", count: summary.stage_breakdown.Saved || 0, dot: "dot-amber", max: totalCount },
      { key: "applied", label: "Applied", count: summary.applied_count || 0, dot: "dot-green", max: totalCount },
      { key: "interviewing", label: "Interviewing", count: summary.interviewing_count || 0, dot: "dot-orange", max: totalCount },
      { key: "offer", label: "Offers", count: summary.offers_count || 0, dot: "dot-slate", max: totalCount },
    ];

    funnelContainer.innerHTML = stages.map(s => {
      const heightPercent = s.count > 0 
        ? Math.max(25, Math.min(100, Math.round((s.count / totalCount) * 100)))
        : 15;
      return `
        <div class="funnel-bar-col ${activeStage.toLowerCase() === s.key.toLowerCase() ? 'active' : ''}" 
             onclick="setStageFilter('${s.key}')">
          <div class="bar-pill" style="height: ${heightPercent}%;">
            ${s.count}
          </div>
          <div class="bar-dot-indicator">
            <span class="dot ${s.dot}"></span>
            ${s.label}
          </div>
        </div>
      `;
    }).join("");
  }
}

function renderSpotlightCard() {
  if (!currentMatches || currentMatches.length === 0) return;
  const match = currentMatches[spotlightIndex % currentMatches.length];
  
  const badgeEl = document.getElementById("spotlightBadge");
  const titleEl = document.getElementById("spotlightTitle");
  const subEl = document.getElementById("spotlightSub");
  
  if (badgeEl) badgeEl.textContent = `Top Match • ${match.match_score}% Confidence`;
  if (titleEl) titleEl.textContent = match.job.title;
  if (subEl) subEl.textContent = `${match.job.company} • ${match.job.salary_range || 'Competitive Salary'} • ${match.job.location}`;
}

function cycleSpotlight(direction) {
  if (!currentMatches.length) return;
  spotlightIndex = (spotlightIndex + direction + currentMatches.length) % currentMatches.length;
  renderSpotlightCard();
}

function viewSpotlightDetails() {
  if (!currentMatches.length) return;
  const match = currentMatches[spotlightIndex % currentMatches.length];
  openJobDrawer(match);
}

function renderQuickFeed() {
  const container = document.getElementById("quickJobList");
  if (!container) return;

  const topItems = currentMatches.slice(0, 5);
  container.innerHTML = topItems.map((m, idx) => {
    const initials = m.job.company.substring(0, 2).toUpperCase();
    const isHigh = m.match_score >= 85;
    return `
      <div class="quick-job-row" onclick="openJobDrawerByIndex(${idx})">
        <div class="job-row-left">
          <div class="company-avatar">${initials}</div>
          <div class="job-meta-text">
            <h4>${escapeHtml(m.job.title)}</h4>
            <p>${escapeHtml(m.job.company)} • ${escapeHtml(m.job.location)}</p>
          </div>
        </div>
        <div class="job-row-right">
          <span class="score-badge ${isHigh ? 'score-high' : 'score-mid'}">
            ${m.match_score}%
          </span>
          <button class="quick-action-check" title="Mark as Reviewed" onclick="event.stopPropagation(); updateStatus('${m.job.id}', 'Saved')">
            &#10003;
          </button>
        </div>
      </div>
    `;
  }).join("");
}

// Comprehensive Multi-Dimensional Filter Engine
function applyFilters() {
  const searchVal = document.getElementById("inlineSearch")?.value.trim().toLowerCase() || "";
  const minConfidence = parseFloat(document.getElementById("matchConfidenceSelect")?.value || "0");
  const domainFilter = document.getElementById("roleDomainSelect")?.value || "all";
  const workModeFilter = document.getElementById("workModeSelect")?.value || "all";
  const minSalaryFilter = parseInt(document.getElementById("minSalarySelect")?.value || "0", 10);
  const sortBy = document.getElementById("sortBySelect")?.value || "score";

  let filtered = [...currentMatches];

  // 1. Stage Filter (All, Matched, Saved, Applied, Interviewing, Offer)
  if (activeStage !== "all") {
    filtered = filtered.filter(m => m.status.toLowerCase() === activeStage.toLowerCase());
  }

  // 2. Minimum Match Score Confidence Filter
  if (minConfidence > 0) {
    filtered = filtered.filter(m => m.match_score >= minConfidence);
  }

  // 3. Free Text Search (across Title, Company, Description, Tags)
  if (searchVal) {
    filtered = filtered.filter(m => {
      const blob = `${m.job.title} ${m.job.company} ${m.job.description} ${m.job.tags.join(" ")}`.toLowerCase();
      return blob.includes(searchVal);
    });
  }

  // 4. Role Domain Filter
  if (domainFilter !== "all") {
    filtered = filtered.filter(m => {
      const text = `${m.job.title} ${m.job.tags.join(" ")}`.toLowerCase();
      if (domainFilter === "backend") return text.includes("backend") || text.includes("python") || text.includes("api") || text.includes("fastapi");
      if (domainFilter === "frontend") return text.includes("frontend") || text.includes("react") || text.includes("next.js") || text.includes("ui") || text.includes("web");
      if (domainFilter === "fullstack") return text.includes("fullstack") || text.includes("full-stack");
      if (domainFilter === "cloud") return text.includes("cloud") || text.includes("devops") || text.includes("kubernetes") || text.includes("sre") || text.includes("aws");
      if (domainFilter === "ai") return text.includes("ai") || text.includes("ml") || text.includes("machine learning") || text.includes("llm") || text.includes("nlp");
      return true;
    });
  }

  // 5. Work Mode Filter
  if (workModeFilter === "remote") {
    filtered = filtered.filter(m => m.job.is_remote);
  } else if (workModeFilter === "onsite") {
    filtered = filtered.filter(m => !m.job.is_remote);
  }

  // 6. Minimum Salary Filter
  if (minSalaryFilter > 0) {
    filtered = filtered.filter(m => {
      if (!m.job.salary_range) return false;
      const nums = m.job.salary_range.replace(/,/g, "").match(/\d{5,6}/g);
      if (nums) {
        const maxVal = Math.max(...nums.map(n => parseInt(n, 10)));
        return maxVal >= minSalaryFilter;
      }
      return false;
    });
  }

  // 7. Clickable Skill Filter Chips
  if (activeSkillFilters.size > 0) {
    filtered = filtered.filter(m => {
      const jobTagsLower = m.job.tags.map(t => t.toLowerCase());
      const jobDescLower = m.job.description.toLowerCase();
      for (const requiredSkill of activeSkillFilters) {
        if (!jobTagsLower.includes(requiredSkill) && !jobDescLower.includes(requiredSkill)) {
          return false;
        }
      }
      return true;
    });
  }

  // 8. Sorting
  if (sortBy === "salary") {
    filtered.sort((a, b) => {
      const numA = (a.job.salary_range || "").replace(/,/g, "").match(/\d{5,6}/g);
      const numB = (b.job.salary_range || "").replace(/,/g, "").match(/\d{5,6}/g);
      const valA = numA ? Math.max(...numA.map(Number)) : 0;
      const valB = numB ? Math.max(...numB.map(Number)) : 0;
      return valB - valA;
    });
  } else if (sortBy === "newest") {
    filtered.sort((a, b) => new Date(b.job.published_at) - new Date(a.job.published_at));
  } else {
    // Default: Highest match score
    filtered.sort((a, b) => b.match_score - a.match_score);
  }

  // Update Result Counter
  const counterEl = document.getElementById("matchResultsCounter");
  if (counterEl) {
    counterEl.textContent = `Showing ${filtered.length} of ${currentMatches.length} opportunities matching your resume & filters`;
  }

  renderOpportunitiesTable(filtered);
}

function resetAllFilters() {
  document.getElementById("inlineSearch").value = "";
  document.getElementById("matchConfidenceSelect").value = "0";
  document.getElementById("roleDomainSelect").value = "all";
  document.getElementById("workModeSelect").value = "all";
  document.getElementById("minSalarySelect").value = "0";
  document.getElementById("sortBySelect").value = "score";
  activeStage = "all";
  activeSkillFilters.clear();
  renderSkillFilterChips();

  // Reset stage pills
  document.querySelectorAll(".filter-pill").forEach(p => p.classList.toggle("active", p.getAttribute("data-stage") === "all"));
  applyFilters();
  showToast("All filters reset.");
}

function setStageFilter(stage) {
  activeStage = stage.toLowerCase();
  
  // Highlight filter pills in right card
  document.querySelectorAll(".filter-pill").forEach(pill => {
    pill.classList.toggle("active", pill.getAttribute("data-stage") === activeStage);
  });
  
  // Highlight funnel bar columns
  document.querySelectorAll(".funnel-bar-col").forEach(col => {
    const match = col.textContent.toLowerCase().includes(activeStage);
    col.classList.toggle("active", match);
  });

  applyFilters();
}

function renderOpportunitiesTable(matches) {
  const tbody = document.getElementById("opportunitiesTableBody");
  if (!tbody) return;

  if (!matches || matches.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="5" style="text-align:center; padding: 48px; color: var(--text-dim);">
          <div style="font-size: 24px; margin-bottom: 8px;">🔍</div>
          <div style="font-size: 15px; font-weight: 700; color: var(--text-main);">No opportunities match your current filters</div>
          <div style="font-size: 13px; color: var(--text-muted); margin-top: 4px;">Try lowering your match confidence threshold or clearing specific skill tags.</div>
          <button class="reset-filters-btn" style="margin-top: 14px;" onclick="resetAllFilters()">Reset All Filters</button>
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = matches.map((m, idx) => {
    const isHigh = m.match_score >= 85;
    const isMid = m.match_score >= 70 && m.match_score < 85;
    const badgeClass = isHigh ? 'score-high' : (isMid ? 'score-mid' : '');
    
    const skillsHtml = m.matched_skills.slice(0, 4).map(s => 
      `<span class="opp-skill-tag">&#10003; ${escapeHtml(s)}</span>`
    ).join("");

    return `
      <tr class="opp-row" onclick="openJobDrawerByIndex(${idx}, ${JSON.stringify(m).replace(/"/g, '&quot;')})">
        <td class="opp-primary-col">
          <h4>${escapeHtml(m.job.title)}</h4>
          <p>${escapeHtml(m.job.company)} • ${escapeHtml(m.job.location)} • <span style="color: var(--accent-orange); font-weight: 600;">${m.job.source}</span></p>
        </td>
        <td>
          <span class="score-badge ${badgeClass}" style="${!badgeClass ? 'background: rgba(255,255,255,0.06); color: var(--text-dim);' : ''}">
            ${m.match_score}% Match
          </span>
        </td>
        <td>
          <div class="opp-skills-tag-wrap">${skillsHtml || '<span style="font-size: 11px; color: var(--text-dim);">Domain Match</span>'}</div>
        </td>
        <td class="opp-salary-col">
          ${m.job.salary_range || 'Competitive'}
        </td>
        <td style="text-align: right;">
          <button class="opp-action-btn" onclick="event.stopPropagation(); openJobDrawer(${JSON.stringify(m).replace(/"/g, '&quot;')})">
            Details &amp; Apply &rarr;
          </button>
        </td>
      </tr>
    `;
  }).join("");
}

function openJobDrawerByIndex(index, matchObj) {
  if (matchObj) {
    openJobDrawer(matchObj);
  } else if (currentMatches[index]) {
    openJobDrawer(currentMatches[index]);
  }
}

function openJobDrawer(match) {
  const drawer = document.getElementById("jobDrawer");
  const content = document.getElementById("drawerContent");
  if (!drawer || !content) return;

  const skillsList = match.matched_skills.map(s => 
    `<span style="background: rgba(16,185,129,0.15); color: #34d399; padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 600;">&#10003; ${escapeHtml(s)}</span>`
  ).join(" ");

  const missingList = match.missing_skills.map(s => 
    `<span style="background: rgba(255,255,255,0.06); color: var(--text-dim); padding: 4px 10px; border-radius: 6px; font-size: 12px;">+ ${escapeHtml(s)}</span>`
  ).join(" ");

  content.innerHTML = `
    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px;">
      <span class="score-badge ${match.match_score >= 85 ? 'score-high' : 'score-mid'}" style="font-size: 13px; padding: 5px 12px;">
        ${match.match_score}% Match Score
      </span>
      <span style="font-size: 12px; color: var(--text-dim);">${match.job.source}</span>
    </div>

    <h2 style="font-size: 24px; font-weight: 800; color: #ffffff; margin-bottom: 6px; line-height: 1.25;">
      ${escapeHtml(match.job.title)}
    </h2>
    <div style="font-size: 14px; color: var(--accent-orange); font-weight: 700; margin-bottom: 16px;">
      ${escapeHtml(match.job.company)} • ${escapeHtml(match.job.location)}
      ${match.job.salary_range ? ` • <span style="color:#ffffff;">${escapeHtml(match.job.salary_range)}</span>` : ''}
    </div>

    <div style="background: var(--bg-card-secondary); border: 1px solid var(--border-subtle); border-radius: 12px; padding: 14px; margin-bottom: 20px;">
      <div style="font-size: 11px; text-transform: uppercase; color: var(--text-dim); margin-bottom: 4px; font-weight: 700;">Why You Match</div>
      <div style="font-size: 13px; color: var(--text-main);">${escapeHtml(match.match_rationale)}</div>
    </div>

    <div style="margin-bottom: 20px;">
      <div style="font-size: 12px; font-weight: 700; text-transform: uppercase; color: var(--text-dim); margin-bottom: 8px;">Matching Resume Skills</div>
      <div style="display: flex; flex-wrap: wrap; gap: 6px;">${skillsList || '<span style="font-size: 12px; color: var(--text-dim);">No exact skill overlap</span>'}</div>
    </div>

    ${missingList ? `
    <div style="margin-bottom: 24px;">
      <div style="font-size: 12px; font-weight: 700; text-transform: uppercase; color: var(--text-dim); margin-bottom: 8px;">Additional Role Competencies</div>
      <div style="display: flex; flex-wrap: wrap; gap: 6px;">${missingList}</div>
    </div>
    ` : ''}

    <div style="margin-bottom: 24px;">
      <div style="font-size: 12px; font-weight: 700; text-transform: uppercase; color: var(--text-dim); margin-bottom: 8px;">Position Description</div>
      <div style="font-size: 13px; line-height: 1.6; color: var(--text-muted); max-height: 220px; overflow-y: auto; background: var(--bg-card-secondary); padding: 14px; border-radius: 12px; border: 1px solid var(--border-subtle);">
        ${escapeHtml(match.job.description) || 'Click below to view the official posting and apply.'}
      </div>
    </div>

    <div style="display: flex; gap: 10px; margin-top: auto; padding-top: 20px;">
      <a href="${match.job.url}" target="_blank" rel="noopener noreferrer" class="primary-cta-btn" style="flex: 1; text-align: center; justify-content: center; text-decoration: none;">
        Apply on Company Site &rarr;
      </a>
      <button class="opp-action-btn" onclick="updateStatus('${match.job.id}', 'Applied'); closeDrawer();">
        Mark Applied
      </button>
    </div>
  `;

  drawer.classList.add("active");
}

function closeDrawer() {
  document.getElementById("jobDrawer")?.classList.remove("active");
}

async function updateStatus(jobId, newStatus) {
  try {
    const res = await fetch(`/api/jobs/${jobId}/status?new_status=${newStatus}`, { method: "PATCH" });
    if (res.ok) {
      const match = currentMatches.find(m => m.job.id === jobId);
      if (match) match.status = newStatus;
      applyFilters();
      showToast(`Opportunity marked as '${newStatus}'!`);
    }
  } catch (err) {
    console.error("Failed to update status:", err);
  }
}

// Resume Upload & Parse Handlers
async function handleResumeUpload(file) {
  const uploadStatus = document.getElementById("uploadStatusText");
  const uploadSpinner = document.getElementById("uploadSpinner");
  
  if (uploadStatus) uploadStatus.textContent = `Uploading and parsing ${file.name}...`;
  if (uploadSpinner) uploadSpinner.style.display = "block";

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/api/resume/upload", {
      method: "POST",
      body: formData
    });

    const data = await res.json();
    if (res.ok) {
      if (uploadStatus) uploadStatus.textContent = `Parsing complete! Extracted ${data.profile.skills.length} skills.`;
      setTimeout(() => {
        closeModal("resumeUploadModal");
        loadProfileAndData();
        showToast(`Resume uploaded! Extracted ${data.profile.skills.length} skills & re-scored jobs.`);
      }, 1000);
    } else {
      if (uploadStatus) uploadStatus.textContent = `Error: ${data.detail || 'Upload failed'}`;
    }
  } catch (err) {
    if (uploadStatus) uploadStatus.textContent = `Network error: ${err.message}`;
  } finally {
    if (uploadSpinner) uploadSpinner.style.display = "none";
  }
}

// Paste Resume Text Handler
async function submitPastedResume() {
  const textarea = document.getElementById("pasteResumeTextarea");
  const text = textarea ? textarea.value.trim() : "";
  if (!text || text.length < 20) {
    alert("Please enter at least 20 characters of resume or bio text.");
    return;
  }

  const uploadStatus = document.getElementById("uploadStatusText");
  const uploadSpinner = document.getElementById("uploadSpinner");
  if (uploadStatus) uploadStatus.textContent = "Analyzing pasted resume text...";
  if (uploadSpinner) uploadSpinner.style.display = "block";

  try {
    const res = await fetch("/api/resume/paste", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: text })
    });

    const data = await res.json();
    if (res.ok) {
      if (uploadStatus) uploadStatus.textContent = "Analysis complete!";
      setTimeout(() => {
        closeModal("resumeUploadModal");
        loadProfileAndData();
        showToast(`Pasted resume analyzed! Found ${data.profile.skills.length} skills.`);
      }, 800);
    } else {
      if (uploadStatus) uploadStatus.textContent = `Error: ${data.detail || 'Analysis failed'}`;
    }
  } catch (err) {
    if (uploadStatus) uploadStatus.textContent = `Error: ${err.message}`;
  } finally {
    if (uploadSpinner) uploadSpinner.style.display = "none";
  }
}

// Load Preset Sample Resume
async function loadSampleResumePreset(sampleId) {
  try {
    const res = await fetch(`/api/resume/sample/${sampleId}`, { method: "POST" });
    if (res.ok) {
      const data = await res.json();
      currentProfile = data.profile;
      await loadProfileAndData();
      closeSampleMenu();
      showToast(`Loaded sample profile: ${data.profile.title}!`);
    }
  } catch (err) {
    console.error("Failed to load sample profile:", err);
  }
}

function toggleSampleMenu() {
  document.getElementById("sampleMenu")?.classList.toggle("active");
}

function closeSampleMenu() {
  document.getElementById("sampleMenu")?.classList.remove("active");
}

function switchResumeTab(tab) {
  document.querySelectorAll(".modal-tab-btn").forEach(b => b.classList.remove("active"));
  document.querySelectorAll(".tab-pane").forEach(p => p.style.display = "none");

  if (tab === "upload") {
    document.getElementById("tabUploadBtn")?.classList.add("active");
    document.getElementById("paneUpload").style.display = "block";
  } else if (tab === "paste") {
    document.getElementById("tabPasteBtn")?.classList.add("active");
    document.getElementById("panePaste").style.display = "block";
  } else if (tab === "sample") {
    document.getElementById("tabSampleBtn")?.classList.add("active");
    document.getElementById("paneSample").style.display = "block";
  }
}

// Sync Jobs from Internet
async function syncJobs(showToastAlert = true) {
  const syncBtn = document.getElementById("syncJobsBtn");
  if (syncBtn) syncBtn.classList.add("spinning");

  try {
    const res = await fetch("/api/jobs/sync", { method: "POST" });
    const data = await res.json();
    await loadProfileAndData();
    if (showToastAlert) {
      showToast(`Synced ${data.synced_count} fresh jobs from RemoteOK, Jobicy & Arbeitnow!`);
    }
  } catch (err) {
    console.error("Job sync error:", err);
  } finally {
    if (syncBtn) syncBtn.classList.remove("spinning");
  }
}

// Email Digest Functions
async function previewEmailDigest() {
  const frame = document.getElementById("emailPreviewFrame");
  const threshold = document.getElementById("digestThresholdSelect")?.value || "75";
  if (frame) {
    frame.src = `/api/digest/preview?top_n=5`;
    openModal("emailDigestModal");
  }
}

async function sendTestEmailDigest() {
  const sendBtn = document.getElementById("sendDigestBtn");
  const emailInput = document.getElementById("digestEmailInput");
  const threshold = parseFloat(document.getElementById("digestThresholdSelect")?.value || "75");

  const targetEmail = emailInput ? emailInput.value.trim() : (currentProfile ? currentProfile.email : "alex.mercer@example.com");

  if (sendBtn) sendBtn.textContent = "Dispatching...";

  try {
    const res = await fetch("/api/digest/send", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        recipient_email: targetEmail,
        candidate_name: currentProfile ? currentProfile.full_name : "Candidate",
        top_n: 5,
        min_score: threshold
      })
    });
    const data = await res.json();
    showToast(data.message || `Email digest dispatched to ${targetEmail}!`);
    closeModal("emailDigestModal");
  } catch (err) {
    showToast(`Dispatch failed: ${err.message}`);
  } finally {
    if (sendBtn) sendBtn.textContent = "Send Test Digest Now";
  }
}

// Command Palette Search
function renderPaletteResults(query) {
  const container = document.getElementById("paletteResults");
  if (!container) return;

  const q = query.trim().toLowerCase();
  const filtered = currentMatches.filter(m => 
    m.job.title.toLowerCase().includes(q) ||
    m.job.company.toLowerCase().includes(q) ||
    m.job.tags.some(t => t.toLowerCase().includes(q))
  ).slice(0, 8);

  if (filtered.length === 0) {
    container.innerHTML = `<div style="padding: 14px; text-align: center; color: var(--text-dim); font-size: 13px;">No opportunities found for "${escapeHtml(query)}"</div>`;
    return;
  }

  container.innerHTML = filtered.map((m, idx) => `
    <div class="palette-item" onclick="closeAllModals(); openJobDrawer(${JSON.stringify(m).replace(/"/g, '&quot;')});">
      <div>
        <div style="font-weight: 700; font-size: 14px; color: var(--text-main);">${escapeHtml(m.job.title)}</div>
        <div style="font-size: 12px; color: var(--text-muted);">${escapeHtml(m.job.company)} • ${m.job.location}</div>
      </div>
      <span class="score-badge ${m.match_score >= 85 ? 'score-high' : 'score-mid'}">
        ${m.match_score}%
      </span>
    </div>
  `).join("");
}

// Modal Helpers
function openModal(id) {
  document.getElementById(id)?.classList.add("active");
}

function closeModal(id) {
  document.getElementById(id)?.classList.remove("active");
}

function closeAllModals() {
  document.querySelectorAll(".modal-overlay").forEach(m => m.classList.remove("active"));
}

// Toast Notification
function showToast(message) {
  let toast = document.getElementById("appToast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "appToast";
    toast.style.cssText = `
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: var(--bg-card-secondary);
      color: #ffffff;
      border: 1px solid var(--accent-orange);
      border-radius: 9999px;
      padding: 12px 24px;
      font-size: 14px;
      font-weight: 600;
      box-shadow: 0 10px 30px rgba(0,0,0,0.5);
      z-index: 2000;
      transition: all 0.3s ease;
      opacity: 0;
      transform: translateY(10px);
    `;
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.style.opacity = "1";
  toast.style.transform = "translateY(0)";
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(10px)";
  }, 3500);
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// ========================================================
// Interactive ATS Resume Studio & Open-Source Diagnostic Scorer
// ========================================================

let studioDraftProfile = null;
let studioDebounceTimer = null;
let studioAtsReport = null;

const ATS_POWER_VERBS = [
  "architected", "spearheaded", "engineered", "orchestrated", "scaled", "optimized",
  "automated", "streamlined", "delivered", "implemented", "designed", "built",
  "deployed", "refactored", "accelerated", "pioneered", "mentored", "standardized",
  "established", "reduced", "increased", "maximized", "minimized", "negotiated",
  "formulated", "conceptualized", "executed", "launched", "migrated", "championed"
];

function openResumeStudio() {
  if (!currentProfile) {
    showToast("Loading active candidate profile...");
    return;
  }

  // Clone active profile into draft
  studioDraftProfile = JSON.parse(JSON.stringify(currentProfile));

  // Ensure default work experience structure
  if (!studioDraftProfile.work_history || studioDraftProfile.work_history.length === 0) {
    studioDraftProfile.work_history = [
      {
        company: "Apex Technologies",
        role: "Senior Backend Engineer",
        duration: "2021 - Present",
        highlights: [
          "Architected high-throughput FastAPI microservices handling 2.4M daily requests with 99.99% uptime.",
          "Engineered distributed caching layer using Redis and PostgreSQL, reducing query latency by 45%.",
          "Automated multi-stage Docker container deployments via GitHub Actions, accelerating release cycles by 3x."
        ]
      },
      {
        company: "DataPulse Labs",
        role: "Software Engineer",
        duration: "2018 - 2021",
        highlights: [
          "Built scalable RESTful endpoints in Python for real-time analytics dashboards serving 150k active users.",
          "Optimized database schema and indexing strategies, eliminating query bottlenecks and saving $18k in cloud resources."
        ]
      }
    ];
  }

  if (!studioDraftProfile.education || studioDraftProfile.education.length === 0) {
    studioDraftProfile.education = [
      "B.S. in Computer Science - University of California, Berkeley (2014 - 2018)"
    ];
  }

  // Populate form fields
  document.getElementById("builderFullName").value = studioDraftProfile.full_name || "";
  document.getElementById("builderTitle").value = studioDraftProfile.title || "";
  document.getElementById("builderEmail").value = studioDraftProfile.email || "";
  document.getElementById("builderPhone").value = studioDraftProfile.phone || "";
  document.getElementById("builderLocation").value = (studioDraftProfile.preferred_locations || ["Remote"]).join(" / ");
  document.getElementById("builderSummary").value = studioDraftProfile.summary || "";

  updateSummaryWordCount();
  renderStudioSkills();
  renderStudioExperience();
  renderStudioEducation();
  renderResumeStudioPreview();

  // Switch to editor tab initially
  switchStudioTab("editor");

  // Evaluate ATS diagnostic score immediately
  evaluateStudioATSScore(0);

  openModal("resumeStudioModal");
}

function switchStudioTab(tab) {
  const editorBtn = document.getElementById("studioTabEditorBtn");
  const atsBtn = document.getElementById("studioTabAtsBtn");
  const editorPane = document.getElementById("studioEditorPane");
  const atsPane = document.getElementById("studioAtsPane");

  if (tab === "editor") {
    editorBtn?.classList.add("active");
    atsBtn?.classList.remove("active");
    if (editorPane) editorPane.style.display = "block";
    if (atsPane) atsPane.style.display = "none";
  } else {
    atsBtn?.classList.add("active");
    editorBtn?.classList.remove("active");
    if (editorPane) editorPane.style.display = "none";
    if (atsPane) atsPane.style.display = "block";
  }
}

function updateSummaryWordCount() {
  const summary = document.getElementById("builderSummary")?.value || "";
  const words = summary.trim() ? summary.trim().split(/\s+/).length : 0;
  const badge = document.getElementById("summaryWordCount");
  if (badge) badge.textContent = `${words} words`;
}

function onBuilderInputChange() {
  if (!studioDraftProfile) return;

  studioDraftProfile.full_name = document.getElementById("builderFullName")?.value || "";
  studioDraftProfile.title = document.getElementById("builderTitle")?.value || "";
  studioDraftProfile.email = document.getElementById("builderEmail")?.value || "";
  studioDraftProfile.phone = document.getElementById("builderPhone")?.value || "";
  studioDraftProfile.summary = document.getElementById("builderSummary")?.value || "";

  const loc = document.getElementById("builderLocation")?.value || "";
  studioDraftProfile.preferred_locations = loc ? loc.split("/").map(s => s.trim()) : ["Remote"];

  updateSummaryWordCount();
  renderResumeStudioPreview();
  evaluateStudioATSScore(250);
}

// Skills Management in Studio
function renderStudioSkills() {
  const wrap = document.getElementById("builderSkillsList");
  if (!wrap || !studioDraftProfile) return;

  wrap.innerHTML = (studioDraftProfile.skills || []).map(skill => `
    <span class="studio-skill-chip">
      ${escapeHtml(skill)}
      <span class="remove-chip" onclick="removeStudioSkill('${escapeHtml(skill)}')">&times;</span>
    </span>
  `).join("");
}

function handleNewSkillKey(e) {
  if (e.key === "Enter" || e.key === ",") {
    e.preventDefault();
    addSkillFromInput();
  }
}

function addSkillFromInput() {
  const input = document.getElementById("newSkillInput");
  if (!input || !studioDraftProfile) return;
  const val = input.value.trim().replace(/^,+|,+$/g, "");
  if (!val) return;

  if (!studioDraftProfile.skills.includes(val)) {
    studioDraftProfile.skills.push(val);
    renderStudioSkills();
    renderResumeStudioPreview();
    evaluateStudioATSScore(200);
  }
  input.value = "";
}

function removeStudioSkill(skill) {
  if (!studioDraftProfile) return;
  studioDraftProfile.skills = studioDraftProfile.skills.filter(s => s.toLowerCase() !== skill.toLowerCase());
  renderStudioSkills();
  renderResumeStudioPreview();
  evaluateStudioATSScore(200);
}

// Work Experience Management in Studio
function renderStudioExperience() {
  const container = document.getElementById("builderExperienceList");
  if (!container || !studioDraftProfile) return;

  const exps = studioDraftProfile.work_history || [];
  if (exps.length === 0) {
    container.innerHTML = `<div style="font-size: 13px; color: var(--text-dim); padding: 12px; text-align: center;">No experience entries yet. Click "+ Add Position" above.</div>`;
    return;
  }

  container.innerHTML = exps.map((exp, expIdx) => {
    const bulletsHtml = (exp.highlights || []).map((b, bulletIdx) => {
      const hasMetric = /\b\d+(?:\.\d+)?%|\$\d+|\b\d+\s*(?:k|users|requests|ms|qps|x|fold)\b/i.test(b);
      const firstWord = (b.trim().split(/\s+/)[0] || "").toLowerCase();
      const hasVerb = ATS_POWER_VERBS.includes(firstWord);

      return `
        <div class="bullet-input-row">
          <textarea class="studio-textarea" rows="2" 
                    placeholder="e.g. Architected FastAPI services handling 2.4M requests with 99.99% uptime..."
                    oninput="onBulletChange(${expIdx}, ${bulletIdx}, this.value)">${escapeHtml(b)}</textarea>
          <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 4px;">
            <button type="button" class="delete-bullet-btn" title="Delete bullet" onclick="removeExperienceBullet(${expIdx}, ${bulletIdx})">&times;</button>
            ${hasMetric ? '<span class="metric-tag-indicator" title="Measurable impact detected">Metric ✓</span>' : ''}
            ${hasVerb ? '<span class="verb-tag-indicator" title="Strong action verb detected">Action Verb ✓</span>' : ''}
          </div>
        </div>
      `;
    }).join("");

    return `
      <div class="experience-card-item">
        <div class="exp-card-header">
          <strong style="font-size: 13px; color: var(--text-main);">Position #${expIdx + 1}</strong>
          <button type="button" class="delete-bullet-btn" title="Remove position" onclick="removeExperienceCard(${expIdx})">
            &times; Remove Role
          </button>
        </div>
        
        <div class="form-row-3">
          <div class="form-group">
            <label>Role / Title</label>
            <input type="text" class="studio-input" value="${escapeHtml(exp.role || '')}" 
                   placeholder="e.g. Senior Software Engineer"
                   oninput="onExpChange(${expIdx}, 'role', this.value)">
          </div>
          <div class="form-group">
            <label>Company / Organization</label>
            <input type="text" class="studio-input" value="${escapeHtml(exp.company || '')}" 
                   placeholder="e.g. Apex Technologies"
                   oninput="onExpChange(${expIdx}, 'company', this.value)">
          </div>
          <div class="form-group">
            <label>Employment Duration</label>
            <input type="text" class="studio-input" value="${escapeHtml(exp.duration || '')}" 
                   placeholder="e.g. 2021 - Present"
                   oninput="onExpChange(${expIdx}, 'duration', this.value)">
          </div>
        </div>

        <div style="margin-top: 6px;">
          <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: var(--text-dim); margin-bottom: 6px;">
            Achievements &amp; Responsibilities (Single-Column ATS Bullets)
          </div>
          ${bulletsHtml}
          <button type="button" class="add-bullet-link" onclick="addExperienceBullet(${expIdx})">
            + Add Bullet Point
          </button>
        </div>
      </div>
    `;
  }).join("");
}

function addExperienceCard() {
  if (!studioDraftProfile) return;
  if (!studioDraftProfile.work_history) studioDraftProfile.work_history = [];
  studioDraftProfile.work_history.push({
    company: "Tech Systems Inc.",
    role: "Software Engineer",
    duration: "2020 - 2022",
    highlights: ["Engineered scalable backend services reducing latency by 30%."]
  });
  renderStudioExperience();
  renderResumeStudioPreview();
  evaluateStudioATSScore(200);
}

function removeExperienceCard(expIdx) {
  if (!studioDraftProfile || !studioDraftProfile.work_history) return;
  studioDraftProfile.work_history.splice(expIdx, 1);
  renderStudioExperience();
  renderResumeStudioPreview();
  evaluateStudioATSScore(200);
}

function onExpChange(expIdx, field, val) {
  if (!studioDraftProfile || !studioDraftProfile.work_history[expIdx]) return;
  studioDraftProfile.work_history[expIdx][field] = val;
  renderResumeStudioPreview();
  evaluateStudioATSScore(300);
}

function addExperienceBullet(expIdx) {
  if (!studioDraftProfile || !studioDraftProfile.work_history[expIdx]) return;
  if (!studioDraftProfile.work_history[expIdx].highlights) {
    studioDraftProfile.work_history[expIdx].highlights = [];
  }
  studioDraftProfile.work_history[expIdx].highlights.push(
    "Orchestrated cross-functional deployment pipelines reducing release friction by 50%."
  );
  renderStudioExperience();
  renderResumeStudioPreview();
  evaluateStudioATSScore(200);
}

function removeExperienceBullet(expIdx, bulletIdx) {
  if (!studioDraftProfile || !studioDraftProfile.work_history[expIdx]) return;
  studioDraftProfile.work_history[expIdx].highlights.splice(bulletIdx, 1);
  renderStudioExperience();
  renderResumeStudioPreview();
  evaluateStudioATSScore(200);
}

function onBulletChange(expIdx, bulletIdx, val) {
  if (!studioDraftProfile || !studioDraftProfile.work_history[expIdx]) return;
  studioDraftProfile.work_history[expIdx].highlights[bulletIdx] = val;
  renderResumeStudioPreview();
  evaluateStudioATSScore(300);
}

// Education Management in Studio
function renderStudioEducation() {
  const container = document.getElementById("builderEducationList");
  if (!container || !studioDraftProfile) return;

  const edus = studioDraftProfile.education || [];
  container.innerHTML = edus.map((edu, idx) => `
    <div style="display: flex; gap: 8px; margin-bottom: 8px;">
      <input type="text" class="studio-input" value="${escapeHtml(edu)}"
             placeholder="e.g. B.S. in Computer Science - University of California (2014 - 2018)"
             oninput="onEducationChange(${idx}, this.value)">
      <button type="button" class="delete-bullet-btn" onclick="removeEducationItem(${idx})">&times;</button>
    </div>
  `).join("");
}

function addEducationItem() {
  if (!studioDraftProfile) return;
  if (!studioDraftProfile.education) studioDraftProfile.education = [];
  studioDraftProfile.education.push("B.S. in Software Engineering - Tech University");
  renderStudioEducation();
  renderResumeStudioPreview();
  evaluateStudioATSScore(200);
}

function removeEducationItem(idx) {
  if (!studioDraftProfile || !studioDraftProfile.education) return;
  studioDraftProfile.education.splice(idx, 1);
  renderStudioEducation();
  renderResumeStudioPreview();
  evaluateStudioATSScore(200);
}

function onEducationChange(idx, val) {
  if (!studioDraftProfile || !studioDraftProfile.education) return;
  studioDraftProfile.education[idx] = val;
  renderResumeStudioPreview();
  evaluateStudioATSScore(300);
}

// Render Clean Single-Column Harvard / Greenhouse ATS Paper Preview
function renderResumeStudioPreview() {
  const preview = document.getElementById("atsPaperPreview");
  if (!preview || !studioDraftProfile) return;

  const p = studioDraftProfile;
  const fullName = p.full_name || "Alex Mercer";
  const title = p.title || "Software Engineer";
  const email = p.email || "candidate@example.com";
  const phone = p.phone || "+1 (555) 019-2834";
  const location = (p.preferred_locations && p.preferred_locations.length > 0) ? p.preferred_locations.join(", ") : "Remote";

  // Build Experience HTML
  let experienceHtml = "";
  if (p.work_history && p.work_history.length > 0) {
    experienceHtml = `
      <div class="paper-section-title">Professional Experience</div>
      ${p.work_history.map(w => `
        <div style="margin-bottom: 10px;">
          <div class="paper-job-header">
            <span><strong>${escapeHtml(w.role || 'Software Engineer')}</strong>, <em>${escapeHtml(w.company || 'Company')}</em></span>
            <span style="font-size: 9.5pt; font-weight: normal;">${escapeHtml(w.duration || '2020 - Present')}</span>
          </div>
          ${w.highlights && w.highlights.length > 0 ? `
            <ul>
              ${w.highlights.map(h => `<li>${escapeHtml(h)}</li>`).join("")}
            </ul>
          ` : ''}
        </div>
      `).join("")}
    `;
  }

  // Build Skills HTML
  let skillsHtml = "";
  if (p.skills && p.skills.length > 0) {
    skillsHtml = `
      <div class="paper-section-title">Technical Competencies</div>
      <p style="margin: 4px 0 10px 0; font-size: 10pt; line-height: 1.45;">
        <strong>Core Technologies:</strong> ${p.skills.map(s => escapeHtml(s)).join(" &bull; ")}
      </p>
    `;
  }

  // Build Education HTML
  let educationHtml = "";
  if (p.education && p.education.length > 0) {
    educationHtml = `
      <div class="paper-section-title">Education &amp; Credentials</div>
      <ul style="margin-top: 4px;">
        ${p.education.map(e => `<li>${escapeHtml(e)}</li>`).join("")}
      </ul>
    `;
  }

  preview.innerHTML = `
    <h1>${escapeHtml(fullName)}</h1>
    <div class="paper-contact">
      ${escapeHtml(email)} &bull; ${escapeHtml(phone)} &bull; ${escapeHtml(location)} &bull; ${escapeHtml(title)}
    </div>

    ${p.summary ? `
      <div class="paper-section-title">Professional Summary</div>
      <p style="margin: 4px 0 10px 0; font-size: 10pt; text-align: justify; line-height: 1.45;">
        ${escapeHtml(p.summary)}
      </p>
    ` : ''}

    ${skillsHtml}
    ${experienceHtml}
    ${educationHtml}
  `;
}

// Real-Time ATS Evaluation Engine
function evaluateStudioATSScore(delay = 250) {
  clearTimeout(studioDebounceTimer);
  studioDebounceTimer = setTimeout(async () => {
    if (!studioDraftProfile) return;

    try {
      const res = await fetch("/api/ats/score", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profile: studioDraftProfile })
      });

      if (!res.ok) return;
      const report = await res.json();
      studioAtsReport = report;
      renderAtsReportUI(report);
    } catch (err) {
      console.error("ATS scoring error:", err);
    }
  }, delay);
}

function renderAtsReportUI(report) {
  if (!report) return;

  // Header Score Chip
  const scoreNum = document.getElementById("studioOverallScore");
  const scoreGrade = document.getElementById("studioOverallGrade");
  const scoreStatus = document.getElementById("studioScoreStatus");
  const scoreChip = document.getElementById("studioScoreChip");

  if (scoreNum) scoreNum.textContent = report.overall_score;
  if (scoreGrade) scoreGrade.textContent = `Grade ${report.grade}`;

  if (report.overall_score >= 85) {
    if (scoreStatus) scoreStatus.textContent = "High Screening Efficiency";
    if (scoreChip) scoreChip.style.borderColor = "var(--accent-green)";
    if (scoreNum) scoreNum.style.color = "var(--accent-green)";
  } else if (report.overall_score >= 70) {
    if (scoreStatus) scoreStatus.textContent = "Good Market Alignment";
    if (scoreChip) scoreChip.style.borderColor = "var(--accent-amber)";
    if (scoreNum) scoreNum.style.color = "var(--accent-amber)";
  } else {
    if (scoreStatus) scoreStatus.textContent = "Needs Optimization";
    if (scoreChip) scoreChip.style.borderColor = "var(--accent-orange)";
    if (scoreNum) scoreNum.style.color = "var(--accent-orange)";
  }

  // Quick Metric Tiles
  const metricWords = document.getElementById("atsMetricWordCount");
  const metricVerbs = document.getElementById("atsMetricPowerVerbs");
  const metricQuant = document.getElementById("atsMetricQuantified");
  const metricGaps = document.getElementById("atsMetricGaps");

  if (metricWords) metricWords.textContent = report.readability_word_count;
  if (metricVerbs) metricVerbs.textContent = report.action_verbs_found ? report.action_verbs_found.length : 0;
  if (metricQuant) metricQuant.textContent = report.metrics_detected_count;
  if (metricGaps) metricGaps.textContent = report.missing_market_skills ? report.missing_market_skills.length : 0;

  // Tab Badge Counter
  const suggestionsCount = document.getElementById("studioSuggestionsCount");
  if (suggestionsCount) {
    suggestionsCount.textContent = report.suggestions ? report.suggestions.length : 0;
  }

  // Category Bars
  const catContainer = document.getElementById("atsCategoryBars");
  if (catContainer && report.category_scores) {
    catContainer.innerHTML = report.category_scores.map(cat => {
      const color = cat.score >= 85 ? 'var(--accent-green)' : (cat.score >= 70 ? 'var(--accent-amber)' : 'var(--accent-orange)');
      return `
        <div class="ats-cat-row">
          <div class="ats-cat-row-top">
            <span>${escapeHtml(cat.category)}</span>
            <span style="color: ${color};">${cat.score}% &bull; ${escapeHtml(cat.status)}</span>
          </div>
          <div class="ats-progress-track">
            <div class="ats-progress-fill" style="width: ${cat.score}%; background: ${color};"></div>
          </div>
          <div class="ats-cat-feedback">${escapeHtml(cat.feedback)}</div>
        </div>
      `;
    }).join("");
  }

  // Actionable Suggestions with 1-Click Fixes
  const suggContainer = document.getElementById("studioSuggestionsList");
  if (suggContainer && report.suggestions) {
    if (report.suggestions.length === 0) {
      suggContainer.innerHTML = `
        <div style="padding: 18px; text-align: center; color: var(--accent-green); font-weight: 700; font-size: 13px;">
          🎉 Outstanding! Your resume adheres to all top open-source ATS benchmarks with zero critical flags!
        </div>
      `;
      return;
    }

    suggContainer.innerHTML = report.suggestions.map((sugg, idx) => {
      let fixBtnHtml = "";
      if (sugg.action_type === "add_skill" && report.missing_market_skills && report.missing_market_skills.length > 0) {
        const skillToAdd = report.missing_market_skills[0];
        fixBtnHtml = `
          <button type="button" class="suggestion-fix-btn" onclick="applyAtsSuggestion('add_skill', '${escapeHtml(skillToAdd)}')">
            + Insert '${escapeHtml(skillToAdd)}' into Skills
          </button>
        `;
      } else if (sugg.action_type === "add_metric") {
        fixBtnHtml = `
          <button type="button" class="suggestion-fix-btn" onclick="applyAtsSuggestion('add_metric', '')">
            + Insert Quantified Achievement Template
          </button>
        `;
      } else if (sugg.action_type === "rephrase") {
        fixBtnHtml = `
          <button type="button" class="suggestion-fix-btn" onclick="applyAtsSuggestion('rephrase', '')">
            + Elevate Action Verbs to Power Verbs
          </button>
        `;
      }

      return `
        <div class="ats-suggestion-card severity-${sugg.severity || 'medium'}">
          <div class="suggestion-top-line">
            <span class="suggestion-title">${escapeHtml(sugg.title)}</span>
            <span class="severity-tag ${sugg.severity || 'medium'}">${escapeHtml(sugg.severity || 'Review')}</span>
          </div>
          <div class="suggestion-desc">${escapeHtml(sugg.description)}</div>
          ${sugg.example ? `<div class="suggestion-example">${escapeHtml(sugg.example)}</div>` : ''}
          ${fixBtnHtml}
        </div>
      `;
    }).join("");
  }
}

// 1-Click Fix Action Handler
function applyAtsSuggestion(actionType, extraData) {
  if (!studioDraftProfile) return;

  if (actionType === "add_skill" && extraData) {
    if (!studioDraftProfile.skills.includes(extraData)) {
      studioDraftProfile.skills.push(extraData);
      renderStudioSkills();
      renderResumeStudioPreview();
      evaluateStudioATSScore(50);
      showToast(`Added high-demand skill '${extraData}' to profile!`);
    }
  } else if (actionType === "add_metric") {
    if (studioDraftProfile.work_history && studioDraftProfile.work_history.length > 0) {
      studioDraftProfile.work_history[0].highlights.unshift(
        "Scaled microservices throughput by 42% and reduced median response latency from 450ms to 95ms."
      );
      renderStudioExperience();
      renderResumeStudioPreview();
      evaluateStudioATSScore(50);
      showToast("Added high-impact metric achievement to recent experience!");
    }
  } else if (actionType === "rephrase") {
    if (studioDraftProfile.work_history && studioDraftProfile.work_history.length > 0) {
      const h = studioDraftProfile.work_history[0].highlights;
      if (h && h.length > 0) {
        h[0] = "Architected and delivered scalable distributed systems with 99.99% availability.";
        renderStudioExperience();
        renderResumeStudioPreview();
        evaluateStudioATSScore(50);
        showToast("Rephrased achievements with verified power verbs!");
      }
    }
  }
}

// Save Resume Studio Profile and Re-Rank All Jobs
async function saveResumeStudio() {
  if (!studioDraftProfile) return;

  const saveBtn = document.getElementById("saveStudioBtn");
  if (saveBtn) {
    saveBtn.textContent = "Saving & Re-ranking...";
    saveBtn.disabled = true;
  }

  try {
    const res = await fetch("/api/resume/builder/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(studioDraftProfile)
    });

    const data = await res.json();
    if (res.ok) {
      currentProfile = data.profile;
      await loadProfileAndData();
      closeModal("resumeStudioModal");
      showToast(`🎉 Resume saved! Re-ranked all 51+ jobs with updated ATS match vectors!`);
    } else {
      showToast(`Error: ${data.detail || 'Save failed'}`);
    }
  } catch (err) {
    showToast(`Network error: ${err.message}`);
  } finally {
    if (saveBtn) {
      saveBtn.textContent = "💾 Save & Set Active Profile";
      saveBtn.disabled = false;
    }
  }
}

// Print / Export Clean Single-Column ATS PDF
function printATSResume() {
  window.print();
}

// Switch Mobile Studio Pane (Editor Form vs ATS Report vs ATS Paper Preview)
function switchMobileStudioPane(pane) {
  const gridBody = document.querySelector(".studio-grid-body");
  const tabEditor = document.getElementById("mobTabEditorBtn");
  const tabAts = document.getElementById("mobTabAtsBtn");
  const tabPreview = document.getElementById("mobTabPreviewBtn");

  if (tabEditor) tabEditor.classList.remove("active");
  if (tabAts) tabAts.classList.remove("active");
  if (tabPreview) tabPreview.classList.remove("active");

  if (pane === "editor") {
    if (tabEditor) tabEditor.classList.add("active");
    if (gridBody) gridBody.classList.remove("show-preview");
    switchStudioTab("editor");
  } else if (pane === "ats") {
    if (tabAts) tabAts.classList.add("active");
    if (gridBody) gridBody.classList.remove("show-preview");
    switchStudioTab("ats");
  } else if (pane === "preview") {
    if (tabPreview) tabPreview.classList.add("active");
    if (gridBody) gridBody.classList.add("show-preview");
  }
}


