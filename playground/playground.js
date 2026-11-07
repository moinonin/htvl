/* HTVL playground - compiles the editor contents live with the real Python
 * compiler, running in the browser via Pyodide. */

"use strict";

const PYODIDE_VERSION = "0.29.5";
const PYODIDE_BASE = `https://cdn.jsdelivr.net/npm/pyodide@${PYODIDE_VERSION}/`;

const SAMPLE = `$DOCTYPE_htvl
$htvl
$head
  $(title '' 'HTVL playground')
  $meta
$_head
$body
  $(nav 'hero')
    $(a 'brand' './' 'HTVL' '' '' '' '')$_a
  $_nav

  $(div 'card')
    $(h 1 '' 'title' 'Write short, get HTML' '')
    $(p '' '' 'You are editing HTVL. This pane is compiled by the real Python compiler, running in your browser.' '')
    $_p
    $(ul 'actions')
      $(li '')
        $(a 'button' 'https://github.com/moinonin/htvl' 'primary' '' '' '' 'Read the grammar')$_a
      $_li
      $(li '')
        $(a 'button' '#' '' '' '' '' 'Toggle modern mode above')$_a
      $_li
    $_ul
  $_div
$_body
$_htvl
`;

const editor = document.getElementById("editor");
const preview = document.getElementById("preview");
const output = document.getElementById("output");
const status = document.getElementById("status");
const counts = document.getElementById("counts");
const legacyButton = document.getElementById("mode-legacy");
const modernButton = document.getElementById("mode-modern");

let modern = false;
let compileFromPython = null;
let timer = null;

function setStatus(text, broken) {
  status.textContent = text;
  status.classList.toggle("broken", Boolean(broken));
}

function loadScript(src) {
  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = src;
    script.onload = resolve;
    script.onerror = () => reject(new Error(`could not load ${src}`));
    document.head.appendChild(script);
  });
}

async function installPackage(pyodide) {
  const manifest = await (await fetch("lib/manifest.json")).json();
  pyodide.FS.mkdirTree("/home/pyodide/htvl");
  for (const name of manifest.files) {
    const code = await (await fetch(`lib/htvl/${name}`)).text();
    pyodide.FS.writeFile(`/home/pyodide/htvl/${name}`, code);
  }
  pyodide.runPython(
    "import sys; sys.path.insert(0, '/home/pyodide');" +
      "from htvl import compile_source;" +
      "def compile(src, modern=False):\n" +
      "    return compile_source(src, modern=modern)\n"
  );
  return pyodide.globals.get("compile");
}

function escapeHtml(text) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function compileNow() {
  if (!compileFromPython) return;
  const source = editor.value;
  let html;
  try {
    html = String(compileFromPython(source, { modern: modern }));
  } catch (error) {
    const firstLine = String(error).split("\n").filter(Boolean).slice(-1)[0];
    setStatus(firstLine || String(error), true);
    return;
  }
  preview.srcdoc = html;
  output.textContent = html;
  const sourceLines = source.split("\n").length;
  const outputLines = html.replace(/\n$/, "").split("\n").length;
  counts.textContent = `${sourceLines} lines in, ${outputLines} out`;
  setStatus(`compiled with htvl (${modern ? "modern" : "legacy"})`);
}

function scheduleCompile() {
  if (timer) clearTimeout(timer);
  timer = setTimeout(compileNow, 150);
}

function setMode(next) {
  modern = next;
  legacyButton.classList.toggle("active", !modern);
  modernButton.classList.toggle("active", modern);
  compileNow();
}

async function boot() {
  editor.value = SAMPLE;
  editor.addEventListener("input", scheduleCompile);
  legacyButton.addEventListener("click", () => setMode(false));
  modernButton.addEventListener("click", () => setMode(true));
  try {
    await loadScript(`${PYODIDE_BASE}pyodide.js`);
    const pyodide = await loadPyodide({ indexURL: PYODIDE_BASE });
    compileFromPython = await installPackage(pyodide);
    compileNow();
  } catch (error) {
    setStatus(String(error.message || error), true);
  }
}

boot();
