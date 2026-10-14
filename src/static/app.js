const fileInput = document.querySelector('#csv-file');
const dropZone = document.querySelector('#drop-zone');
const dropTitle = document.querySelector('#drop-title');
const dropSubtitle = document.querySelector('#drop-subtitle');
const fileMeta = document.querySelector('#file-meta');
const fileName = document.querySelector('#file-name');
const fileSize = document.querySelector('#file-size');
const fieldGrid = document.querySelector('#field-grid');
const textColumn = document.querySelector('#text-column');
const goldColumn = document.querySelector('#gold-column');
const taskDescription = document.querySelector('#task-description');
const labelsInput = document.querySelector('#labels');
const promptNote = document.querySelector('#prompt-note');
const csvPreview = document.querySelector('#csv-preview');
const previewTableWrap = document.querySelector('#preview-table-wrap');
const runButton = document.querySelector('#run-button');
const formError = document.querySelector('#form-error');
const emptyState = document.querySelector('#empty-state');
const loadingState = document.querySelector('#loading-state');
const loadingTitle = document.querySelector('#loading-title');
const loadingCopy = document.querySelector('#loading-copy');
const analysisResults = document.querySelector('#analysis-results');
const resultCount = document.querySelector('#result-count');
const metricsGrid = document.querySelector('#metrics-grid');
const tableWrap = document.querySelector('#table-wrap');
const tableFootnote = document.querySelector('#table-footnote');
const exportButton = document.querySelector('#export-button');

let selectedFile = null;
let inspectedRows = 0;
let analysis = null;
let activeView = 'wide';

function formatSize(bytes) {
  return bytes < 1024 * 1024 ? `${(bytes / 1024).toFixed(1)} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function showError(message) {
  formError.textContent = message;
  formError.hidden = false;
}

function clearError() {
  formError.textContent = '';
  formError.hidden = true;
}

function updateRunButton() {
  runButton.disabled = !selectedFile || !textColumn.value || !taskDescription.value.trim() || !labelsInput.value.trim();
}

function setBusy(busy) {
  loadingState.hidden = !busy;
  emptyState.hidden = busy || Boolean(analysis);
  analysisResults.hidden = busy || !analysis;
  runButton.disabled = busy || !selectedFile || !textColumn.value;
  if (busy) {
    resultCount.textContent = 'RUNNING';
    loadingTitle.textContent = 'Classifying your rows';
    loadingCopy.textContent = `Running each row through the prompt set. ${inspectedRows.toLocaleString()} rows can take a little while.`;
  }
}

async function inspectFile(file) {
  clearError();
  analysis = null;
  selectedFile = file;
  if (!file || (!file.name.toLowerCase().endsWith('.csv') && file.type !== 'text/csv')) {
    selectedFile = null;
    fileInput.value = '';
    showError('Choose a .csv file to continue.');
    return;
  }
  if (file.size > 50 * 1024 * 1024) {
    selectedFile = null;
    fileInput.value = '';
    showError('This file is over the 50 MB upload limit.');
    return;
  }

  fileMeta.hidden = false;
  fileName.textContent = file.name;
  fileSize.textContent = formatSize(file.size);
  dropTitle.textContent = 'CSV selected';
  dropSubtitle.textContent = 'Choose another file to replace it';
  emptyState.hidden = true;
  analysisResults.hidden = true;
  loadingState.hidden = false;
  loadingTitle.textContent = 'Reading your columns';
  loadingCopy.textContent = 'Checking the CSV and loading a small preview.';

  try {
    const body = new FormData();
    body.append('file', file);
    const response = await fetch('/inspect', { method: 'POST', body });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Could not read this CSV.');
    inspectedRows = data.rows;
    labelsInput.value = (data.suggested_labels || []).join(', ');
    fillColumnOptions(data.columns, data.preview);
    fieldGrid.hidden = false;
    csvPreview.hidden = false;
    promptNote.hidden = false;
    loadingState.hidden = true;
    emptyState.hidden = false;
    resultCount.textContent = `${data.rows.toLocaleString()} ROWS`;
    emptyState.querySelector('h3').textContent = 'Ready when you are.';
    emptyState.querySelector('p').textContent = `${data.rows.toLocaleString()} rows found. Select the text field and categories, then run the analysis.`;
    updateRunButton();
  } catch (error) {
    loadingState.hidden = true;
    emptyState.hidden = false;
    selectedFile = null;
    fileMeta.hidden = true;
    showError(error.message);
    updateRunButton();
  }
}

function fillColumnOptions(columns, preview) {
  textColumn.replaceChildren();
  goldColumn.replaceChildren();
  const placeholder = document.createElement('option');
  placeholder.value = '';
  placeholder.textContent = 'Choose a column';
  textColumn.append(placeholder);
  const noGold = document.createElement('option');
  noGold.value = '';
  noGold.textContent = 'None';
  goldColumn.append(noGold);

  for (const column of columns) {
    const textOption = new Option(column, column);
    textColumn.add(textOption);
    goldColumn.add(new Option(column, column));
  }
  const textCandidate = columns.find((column) => /^(text|content|message|complaint|description|review|comment)$/i.test(column));
  const goldCandidate = columns.find((column) => /^(gold|label|target|category|class)$/i.test(column));
  if (textCandidate) textColumn.value = textCandidate;
  else if (columns.length) textColumn.value = columns[0];
  if (goldCandidate) goldColumn.value = goldCandidate;
  previewRows = preview;
  renderPreview(columns);
}

let previewRows = [];

async function runAnalysis() {
  clearError();
  const labels = labelsInput.value.split(',').map((label) => label.trim()).filter(Boolean);
  if (labels.length < 2) {
    showError('Enter at least two labels, separated by commas.');
    return;
  }
  if (!taskDescription.value.trim()) {
    showError('Describe what the text should be classified as.');
    return;
  }
  setBusy(true);
  try {
    const body = new FormData();
    body.append('file', selectedFile);
    body.append('text_column', textColumn.value);
    body.append('gold_column', goldColumn.value);
    body.append('task_description', taskDescription.value.trim());
    body.append('labels', labels.join(','));
    const response = await fetch('/analyze', { method: 'POST', body });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Analysis failed.');
    analysis = data;
    activeView = 'wide';
    renderAnalysis();
  } catch (error) {
    analysis = null;
    setBusy(false);
    resultCount.textContent = 'ERROR';
    emptyState.hidden = false;
    showError(error.message);
  }
}

function renderPreview(columns) {
  const table = document.createElement('table');
  table.className = 'preview-table';
  const head = document.createElement('thead');
  const header = document.createElement('tr');
  for (const column of columns.slice(0, 4)) {
    const cell = document.createElement('th');
    cell.textContent = column;
    header.append(cell);
  }
  head.append(header);
  const body = document.createElement('tbody');
  for (const row of previewRows) {
    const rowElement = document.createElement('tr');
    for (const column of columns.slice(0, 4)) {
      const cell = document.createElement('td');
      cell.textContent = row[column] == null ? '' : String(row[column]);
      rowElement.append(cell);
    }
    body.append(rowElement);
  }
  table.append(head, body);
  previewTableWrap.replaceChildren(table);
}

function renderAnalysis() {
  const summary = analysis.summary;
  const metrics = [
    ['Rows analyzed', Number(summary.n_examples).toLocaleString(), false],
    ['Prompt variants', summary.n_prompts, false],
    ['Label shift rate', `${(summary.flip_rate * 100).toFixed(1)}%`, true],
    ['Full agreement', `${(summary.full_agreement_rate * 100).toFixed(1)}%`, false],
  ];
  metricsGrid.replaceChildren(...metrics.map(([label, value, accent]) => {
    const item = document.createElement('div');
    item.className = 'metric';
    const title = document.createElement('span');
    title.className = 'metric-label';
    title.textContent = label;
    const number = document.createElement('span');
    number.className = `metric-value${accent ? ' accent' : ''}`;
    number.textContent = value;
    item.append(title, number);
    return item;
  }));
  resultCount.textContent = `${Number(summary.n_examples).toLocaleString()} ROWS ANALYZED`;
  loadingState.hidden = true;
  emptyState.hidden = true;
  analysisResults.hidden = false;
  document.querySelectorAll('.result-tab').forEach((tab) => {
    const active = tab.dataset.view === activeView;
    tab.classList.toggle('active', active);
    tab.setAttribute('aria-selected', String(active));
  });
  renderTable();
}

function renderTable() {
  const allRows = analysis[activeView] || [];
  const rows = allRows.slice(0, 100);
  tableWrap.replaceChildren();
  if (!rows.length) {
    const message = document.createElement('p');
    message.className = 'empty-table';
    message.textContent = activeView === 'disagreements' ? 'No label shifts. All prompt variants agreed on every row.' : 'No rows to display.';
    tableWrap.append(message);
    tableFootnote.textContent = '';
    return;
  }
  const columns = Object.keys(rows[0]);
  const table = document.createElement('table');
  table.className = 'data-table';
  const head = document.createElement('thead');
  const headerRow = document.createElement('tr');
  for (const column of columns) {
    const cell = document.createElement('th');
    cell.textContent = column.replaceAll('_', ' ');
    headerRow.append(cell);
  }
  head.append(headerRow);
  const body = document.createElement('tbody');
  for (const row of rows) {
    const rowElement = document.createElement('tr');
    for (const column of columns) {
      const cell = document.createElement('td');
      const value = row[column];
      if (column === 'majority_label' || column === 'parsed_label') {
        const tag = document.createElement('span');
        tag.className = 'label-tag';
        tag.textContent = value == null ? '' : String(value);
        cell.append(tag);
      } else if (typeof value === 'boolean') {
        cell.textContent = value ? 'Yes' : 'No';
      } else {
        cell.textContent = value == null ? '' : String(value);
      }
      rowElement.append(cell);
    }
    body.append(rowElement);
  }
  table.append(head, body);
  tableWrap.append(table);
  tableFootnote.textContent = allRows.length > 100
    ? `Showing 100 of ${allRows.length.toLocaleString()} rows. Export to download the complete table.`
    : `${allRows.length.toLocaleString()} rows · ${analysis.model}`;
}

function exportTable() {
  if (!analysis) return;
  const rows = analysis[activeView] || [];
  if (!rows.length) return;
  const columns = Object.keys(rows[0]);
  const escapeCsv = (value) => `"${String(value ?? '').replaceAll('"', '""')}"`;
  const content = [columns.map(escapeCsv).join(','), ...rows.map((row) => columns.map((column) => escapeCsv(row[column])).join(','))].join('\r\n');
  const url = URL.createObjectURL(new Blob([content], { type: 'text/csv;charset=utf-8' }));
  const link = document.createElement('a');
  link.href = url;
  link.download = `${activeView}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}

fileInput.addEventListener('change', () => inspectFile(fileInput.files[0]));
document.querySelector('#remove-file').addEventListener('click', () => {
  selectedFile = null;
  analysis = null;
  fileInput.value = '';
  fileMeta.hidden = true;
  fieldGrid.hidden = true;
  csvPreview.hidden = true;
  promptNote.hidden = true;
  dropTitle.textContent = 'Drop your CSV here';
  dropSubtitle.innerHTML = 'or <span class="browse-link">browse files</span> · up to 50 MB';
  resultCount.textContent = 'AWAITING CSV';
  analysisResults.hidden = true;
  emptyState.hidden = false;
  emptyState.querySelector('h3').textContent = 'Your results will land here.';
  emptyState.querySelector('p').textContent = 'Choose a CSV and text column to see prompt agreement, label shifts, and row-level predictions.';
  clearError();
  updateRunButton();
});
runButton.addEventListener('click', runAnalysis);
textColumn.addEventListener('change', updateRunButton);
taskDescription.addEventListener('input', updateRunButton);
labelsInput.addEventListener('input', updateRunButton);
exportButton.addEventListener('click', exportTable);
document.querySelectorAll('.result-tab').forEach((tab) => tab.addEventListener('click', () => {
  activeView = tab.dataset.view;
  document.querySelectorAll('.result-tab').forEach((item) => {
    const active = item === tab;
    item.classList.toggle('active', active);
    item.setAttribute('aria-selected', String(active));
  });
  renderTable();
}));

for (const eventName of ['dragenter', 'dragover']) {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.add('is-over');
  });
}
for (const eventName of ['dragleave', 'drop']) {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.remove('is-over');
  });
}
dropZone.addEventListener('drop', (event) => {
  const file = event.dataTransfer.files[0];
  if (file) inspectFile(file);
});