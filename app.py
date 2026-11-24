#!/usr/bin/env python3
"""
Registration National - single-file prototype (Python 3.8+, standard library only).

Run:      python app.py
Open:     http://127.0.0.1:8000
Phones:   python app.py --host 0.0.0.0   then open http://<this-computer-ip>:8000

What it does
  * Serves the web app (CHW mobile view, registrar portal, admin console).
  * Provides the Sync API (REST/JSON) and stores all data in SQLite
    (registration_national.db next to this file), so every browser and device
    that opens the app shares the same records.
  * CHW devices still keep their own AES-256 encrypted offline queue in the browser.

API
  GET  /api/ping   health check
  GET  /api/db     read the shared database (404 until first seeded)
  POST /api/db     replace the shared database (JSON body)
  POST /api/reset  delete all shared data and re-seed on next page load
"""
import argparse
import json
import os
import socket
import sqlite3
import threading
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "registration_national.db")
MAX_BODY = 20 * 1024 * 1024
LOCK = threading.Lock()

# ---------------------------------------------------------------------------
# Web app (HTML + CSS + JavaScript)
# ---------------------------------------------------------------------------
PAGE = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Registration National</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🍼</text></svg>">
<style>
:root {
  --bg: #edf4f1;
  --card: #fff;
  --fg: #10242b;
  --mut: #587078;
  --pri: #0d5c4b;
  --pri-d: #094536;
  --on: #fff;
  --acc: #f4b81c;
  --bd: #dce7e3;
  --bad: #b3261e;
  --ok: #17803d;
  --warn: #9a6a00;
  --sh: 0 1px 2px #10242b12,0 8px 22px #10242b0f;
}
@media(prefers-color-scheme:dark) {
  :root {
    --bg: #0b1517;
    --card: #13242a;
    --fg: #e8f1ef;
    --mut: #92a9ac;
    --pri: #2fa98d;
    --pri-d: #4cc2a6;
    --on: #06241d;
    --bd: #233a40;
    --bad: #ff8f86;
    --ok: #63d78f;
    --warn: #f4b81c;
    --sh: none;
  }
}
* {
  box-sizing: border-box;
}
html {
  scroll-behavior: smooth;
}
body {
  margin: 0;
  font: 16px/1.5 "Segoe UI",system-ui,-apple-system,Roboto,sans-serif;
  background: var(--bg);
  color: var(--fg);
}
h1,h2,h3,h4 {
  margin: 0;
  line-height: 1.2;
  letter-spacing: -.01em;
}
h2 {
  font-size: 22px;
}
h3 {
  font-size: 19px;
}
h4 {
  font-size: 15px;
}
#bar {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 10px 16px;
  background: linear-gradient(135deg,#0b4d3e,#0e6a56);
  color: #fff;
  position: sticky;
  top: 0;
  z-index: 5;
  flex-wrap: wrap;
  border-bottom: 3px solid var(--acc);
}
.brand {
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: 17px;
  font-weight: 700;
}
.logo {
  display: inline-grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 9px;
  background: var(--acc);
  color: #0b4d3e;
}
.logo.big {
  width: 52px;
  height: 52px;
  border-radius: 15px;
  margin-bottom: 16px;
}
.sp {
  flex: 1;
}
#bar select,#bar .pill {
  background: #ffffff1f;
  color: #fff;
  border: 1px solid #ffffff55;
  border-radius: 999px;
  padding: 6px 12px;
  min-height: 36px;
  width: auto;
  font-size: 14px;
}
#bar select option {
  color: #000;
}
.pill:before {
  content: "";
  display: inline-block;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  margin-right: 7px;
  background: #6ff0a0;
}
.pill.off:before {
  background: var(--acc);
}
main {
  max-width: 1000px;
  margin: 0 auto;
  padding: 16px 14px 40px;
}
.phone {
  max-width: 480px;
  margin-left: auto;
  margin-right: auto;
}
.card {
  background: var(--card);
  border: 1px solid var(--bd);
  border-radius: 14px;
  padding: 18px;
  margin: 12px 0;
  box-shadow: var(--sh);
}
.card>button {
  margin-top: 14px;
}
label {
  display: block;
  margin: 14px 0 5px;
  font-size: 14px;
  font-weight: 600;
}
input,select,textarea {
  width: 100%;
  min-height: 48px;
  padding: 11px 13px;
  border: 2px solid var(--bd);
  border-radius: 11px;
  background: var(--bg);
  color: var(--fg);
  font: inherit;
}
input:focus,select:focus,textarea:focus,button:focus-visible {
  outline: none;
  border-color: var(--pri);
  box-shadow: 0 0 0 4px #f4b81c66;
}
button {
  min-height: 48px;
  background: var(--pri);
  color: var(--on);
  border: 0;
  border-radius: 11px;
  padding: 10px 18px;
  font: inherit;
  font-weight: 600;
  cursor: pointer;
  transition: transform .08s,background .15s;
}
button:hover {
  background: var(--pri-d);
}
button:active {
  transform: scale(.98);
}
button.ghost {
  background: transparent;
  color: var(--pri);
  border: 2px solid var(--pri);
}
button.ghost:hover {
  background: #0d5c4b14;
}
button.ghost.light {
  color: #fff;
  border-color: #ffffff88;
  min-height: 36px;
  padding: 4px 14px;
  border-radius: 999px;
}
button.text {
  background: none;
  color: var(--mut);
  min-height: 36px;
  padding: 4px 8px;
}
button.bad {
  background: var(--bad);
  color: #fff;
}
button.cta {
  width: 100%;
  font-size: 17px;
  min-height: 56px;
  background: var(--acc);
  color: #0b2a22;
  box-shadow: var(--sh);
}
button.cta:hover {
  background: #ffc93a;
}
.row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
}
.between {
  justify-content: space-between;
}
.muted {
  color: var(--mut);
  font-size: 14px;
}
.err {
  color: var(--bad);
  font-size: 14px;
  margin-top: 5px;
  font-weight: 600;
}
.hint {
  color: var(--mut);
  font-size: 13px;
  margin-top: 4px;
}
.chip {
  display: inline-block;
  padding: 3px 11px;
  border-radius: 999px;
  background: #0d5c4b18;
  color: var(--pri);
  font-size: 13px;
  font-weight: 600;
}
.chip.big {
  background: #d3f2dd;
  color: #0e5a29;
  font-size: 15px;
  margin-top: 8px;
}
.greet {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 10px;
  flex-wrap: wrap;
  margin: 6px 0 4px;
}
.banner {
  background: #fff3cf;
  color: #5b4300;
  border: 1px solid #f1d27a;
  border-radius: 11px;
  padding: 11px 14px;
  margin: 10px 0;
  font-size: 14px;
}
.hero {
  background: radial-gradient(circle at 88% 12%,#f4b81c40,transparent 42%),linear-gradient(135deg,#0b4d3e,#10806a);
  color: #fff;
  border-radius: 20px;
  padding: 30px 24px;
  margin: 6px auto 8px;
  max-width: 480px;
}
.hero h1 {
  font-size: clamp(26px,6vw,34px);
  max-width: 14em;
}
.hero p {
  margin: 12px 0 0;
  opacity: .92;
  max-width: 30em;
}
.demos {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-top: 12px;
}
button.demo {
  background: var(--bg);
  color: var(--fg);
  border: 2px solid var(--bd);
  text-align: left;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  padding: 10px 12px;
}
button.demo:hover {
  border-color: var(--pri);
  background: var(--bg);
}
button.demo span {
  font-weight: 400;
  font-size: 13px;
  color: var(--mut);
}
.tabs {
  display: inline-flex;
  gap: 4px;
  background: var(--card);
  border: 1px solid var(--bd);
  border-radius: 999px;
  padding: 4px;
  margin: 12px 0 4px;
  flex-wrap: wrap;
}
.tabs button {
  min-height: 38px;
  background: transparent;
  color: var(--fg);
  padding: 6px 16px;
  border-radius: 999px;
}
.tabs button.on {
  background: var(--pri);
  color: var(--on);
}
.tiles {
  display: grid;
  grid-template-columns: repeat(auto-fit,minmax(96px,1fr));
  gap: 10px;
  margin: 12px 0;
}
.tile {
  background: var(--card);
  border: 1px solid var(--bd);
  border-radius: 13px;
  padding: 12px 14px;
  box-shadow: var(--sh);
}
.tile b {
  display: block;
  font-size: 28px;
  line-height: 1.1;
}
.tile span {
  font-size: 13px;
  color: var(--mut);
}
.tile.warn b {
  color: var(--warn);
}
.tile.ok b {
  color: var(--ok);
}
.tile.bad b {
  color: var(--bad);
}
.rec {
  background: var(--card);
  border: 1px solid var(--bd);
  border-left: 6px solid var(--bd);
  border-radius: 13px;
  padding: 14px 16px;
  margin: 10px 0;
  box-shadow: var(--sh);
}
.rec[data-s=Queued] {
  border-left-color: var(--acc);
}
.rec[data-s=Synced] {
  border-left-color: #2f7fd0;
}
.rec[data-s=Approved] {
  border-left-color: var(--ok);
}
.rec[data-s=Flagged] {
  border-left-color: var(--bad);
}
.empty {
  text-align: center;
  padding: 30px 10px;
  color: var(--mut);
}
.badge {
  padding: 3px 11px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
}
.Draft {
  background: #e3e7ea;
  color: #33414a;
}
.Queued {
  background: #fff0c2;
  color: #6b4e00;
}
.Synced {
  background: #d6e9ff;
  color: #0b3d73;
}
.Approved {
  background: #d3f2dd;
  color: #0e5a29;
}
.Flagged {
  background: #ffd9d6;
  color: #8a1c14;
}
.steps {
  display: flex;
  gap: 5px;
  margin: 10px 0 14px;
}
.steps i {
  flex: 1;
  height: 6px;
  border-radius: 3px;
  background: var(--bd);
}
.steps i.done {
  background: var(--pri);
}
.steps i.cur {
  background: var(--acc);
}
.seg {
  display: flex;
  gap: 8px;
}
.seg button {
  flex: 1;
  background: var(--bg);
  color: var(--fg);
  border: 2px solid var(--bd);
}
.seg button.on {
  background: var(--pri);
  color: var(--on);
  border-color: var(--pri);
}
.actions {
  position: sticky;
  bottom: 0;
  display: flex;
  gap: 8px;
  padding: 14px 0 10px;
  background: linear-gradient(transparent,var(--bg) 28%);
}
.actions button {
  flex: 1;
  margin: 0;
}
.actions button.go {
  flex: 2;
}
.sec {
  padding: 10px 0;
  border-bottom: 1px solid var(--bd);
}
.sec:last-of-type {
  border: 0;
}
dl {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 3px 14px;
  margin: 6px 0 0;
}
dt {
  color: var(--mut);
  font-size: 14px;
}
dd {
  margin: 0;
  font-weight: 600;
  word-break: break-word;
}
.meter {
  height: 7px;
  background: var(--bd);
  border-radius: 4px;
  width: 96px;
  margin-bottom: 3px;
}
.meter i {
  display: block;
  height: 100%;
  background: var(--ok);
  border-radius: 4px;
}
.scroll {
  overflow-x: auto;
}
table {
  width: 100%;
  border-collapse: collapse;
}
th,td {
  padding: 11px 10px;
  border-bottom: 1px solid var(--bd);
  text-align: left;
  vertical-align: top;
}
th {
  font-size: 13px;
  color: var(--mut);
  font-weight: 600;
}
tr:hover td {
  background: #0d5c4b0b;
}
td button {
  min-height: 36px;
  padding: 4px 12px;
  margin: 0;
}
td input,td select {
  min-height: 38px;
  padding: 6px 8px;
}
.filters {
  display: grid;
  grid-template-columns: repeat(auto-fit,minmax(150px,1fr));
  gap: 12px;
}
.thumb {
  max-width: 100%;
  max-height: 200px;
  margin-top: 10px;
  border-radius: 10px;
}
.modal {
  position: fixed;
  inset: 0;
  background: #06141199;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 14px;
  z-index: 20;
}
.modal .card {
  max-width: 540px;
  width: 100%;
  max-height: 92vh;
  overflow: auto;
  margin: 0;
}
#toast {
  position: fixed;
  left: 50%;
  bottom: 24px;
  transform: translate(-50%,30px);
  background: #10242b;
  color: #fff;
  padding: 12px 18px;
  border-radius: 12px;
  opacity: 0;
  transition: .25s;
  z-index: 30;
  max-width: 90%;
  box-shadow: 0 8px 24px #0006;
  border-left: 5px solid var(--acc);
}
#toast.show {
  opacity: 1;
  transform: translate(-50%,0);
}
footer {
  text-align: center;
  color: var(--mut);
  font-size: 13px;
  padding: 10px 20px 30px;
}
@media(prefers-reduced-motion:reduce) {
  * {
    transition: none!important;
  }
}

/* ---------- Backgrounds, dashboard and tints ---------- */
:root {
  --t1: #0d5c4b2e;
  --t2: #f4b81c33;
}
body[data-role="registrar"] { --t1: #0f6e8c2e; }
body[data-role="admin"] { --t1: #0b4d3e40; --t2: #f4b81c40; }
@media (prefers-color-scheme: dark) {
  :root { --t1: #2fa98d22; --t2: #f4b81c18; }
}
body {
  min-height: 100vh;
  background-color: var(--bg);
  background-image: radial-gradient(900px 440px at 100% -60px, var(--t2), transparent 62%), radial-gradient(820px 540px at -10% 0, var(--t1), transparent 62%);
  background-repeat: no-repeat;
}
.center { text-align: center; }
.tile.warn { background: #fff5d6; border-color: #f1d27a; }
.tile.ok { background: #e1f5e8; border-color: #b5e2c4; }
.tile.bad { background: #ffe6e3; border-color: #f3bbb5; }
@media (prefers-color-scheme: dark) {
  .tile.warn { background: #2e2a14; border-color: #5a4d17; }
  .tile.ok { background: #14301f; border-color: #1f5236; }
  .tile.bad { background: #36191a; border-color: #6a2a2b; }
}
.card > h4 { margin-bottom: 10px; }
.grid2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 12px; }
.grid2 > .card { margin: 0; }
.bars { display: flex; gap: 8px; height: 170px; }
.bcol { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 4px; }
.bcol b { font-size: 13px; }
.bcol small { font-size: 12px; color: var(--mut); }
.bw { flex: 1; width: 100%; display: flex; align-items: flex-end; }
.bw i { display: block; width: 100%; min-height: 3px; border-radius: 6px 6px 2px 2px; background: linear-gradient(180deg, var(--acc), var(--pri)); }
.stack { display: flex; height: 16px; border-radius: 8px; overflow: hidden; background: var(--bd); }
.stack i { display: block; height: 100%; }
.legend { display: flex; flex-wrap: wrap; gap: 6px 14px; margin-top: 10px; font-size: 13px; color: var(--mut); }
.lg i { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 6px; }
.lrow { display: grid; grid-template-columns: 1fr 110px auto; gap: 10px; align-items: center; padding: 8px 0; border-bottom: 1px solid var(--bd); }
.lrow:last-child { border: 0; }
.meter.wide { width: 100%; margin: 0; }
.start { background: #fff8e1; border-color: #f1d27a; }
.start ol { margin: 6px 0 0; padding-left: 20px; }
@media (prefers-color-scheme: dark) { .start { background: #2e2a14; border-color: #5a4d17; } }

/* ---------- Dark sunrise over the hills (fixed background scene) ---------- */
:root { --ink: #fbeedd; --ink-mut: #e9c9b0; }
body {
  background-color: #0a0820;
  background-image: none;
}
#scene {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background: #0a0820;
}
#scene svg { width: 100%; height: 100%; display: block; }
#bar, main, footer { position: relative; z-index: 1; }
/* main sits above the footer so record pop-ups are never covered by the footer text */
main { z-index: 2; }
#bar { position: sticky; z-index: 5; }
/* Text that sits directly on the scene (not inside a card) */
.greet, .greet h2, .greet .muted, main > p, main > h3, main > .muted, footer { color: var(--ink); }
.greet .muted, main > p.muted, main > h3 .muted, footer { color: var(--ink-mut); }
.greet, main > h3, main > p { text-shadow: 0 1px 10px #0008; }
.greet .chip { background: #ffffff26; color: #ffe9c7; text-shadow: none; }
button.text { color: var(--ink); }
main > p > button.ghost { background: #0a082066; color: var(--ink); border-color: #ffffff44; }
.card { background: color-mix(in srgb, var(--card) 94%, transparent); backdrop-filter: blur(6px); -webkit-backdrop-filter: blur(6px); }
.tabs { background: color-mix(in srgb, var(--card) 92%, transparent); }
@media (prefers-color-scheme: dark) {
  .card { background: color-mix(in srgb, var(--card) 88%, transparent); }
}
/* Motion: the sun lifts once, the glow breathes, mist drifts, a few stars twinkle */
.sun { animation: sunrise 7s cubic-bezier(.2,.7,.2,1) both; }
.pulse { animation: breathe 9s ease-in-out infinite; }
.mist { animation: drift 38s ease-in-out infinite alternate; }
.mist.m2 { animation-duration: 52s; animation-direction: alternate-reverse; }
.tw { animation: twinkle 4.5s ease-in-out infinite; }
@keyframes sunrise { from { transform: translateY(95px); opacity: .6; } to { transform: none; opacity: 1; } }
@keyframes breathe { 0%,100% { opacity: .85; } 50% { opacity: 1; } }
@keyframes drift { from { transform: translateX(-60px); } to { transform: translateX(60px); } }
@keyframes twinkle { 0%,100% { opacity: .2; } 50% { opacity: 1; } }
@media (prefers-reduced-motion: reduce) {
  .sun, .pulse, .mist, .tw { animation: none !important; }
}

/* Wider layout for the registrar and admin portals (CHW view stays phone-sized) */
body[data-role="admin"] main,
body[data-role="registrar"] main {
  max-width: 1440px;
}
td select { min-width: 10.5em; }
td input { min-width: 9em; }
td:last-child { white-space: nowrap; }
td:last-child button + button { margin-left: 6px; }

/* Phones: each table row becomes a card, with the column name shown next to each value */
@media (max-width: 760px) {
  main { padding: 12px 10px 32px; }
  .scroll { overflow-x: visible; }
  .scroll table, .scroll tbody, .scroll tr, .scroll td { display: block; width: 100%; }
  .scroll tr.thead { display: none; }
  .scroll tr { border: 1px solid var(--bd); border-radius: 12px; padding: 6px 12px; margin-bottom: 10px; }
  .scroll tr:hover td { background: none; }
  .scroll td { border: 0; padding: 7px 0; display: flex; flex-wrap: wrap; align-items: center; gap: 4px 10px; white-space: normal; overflow-wrap: anywhere; }
  .scroll td[data-label]::before { content: attr(data-label); flex: 0 0 7.5em; font-size: 13px; font-weight: 600; color: var(--mut); }
  .scroll td:empty, .scroll td[colspan]:empty { display: none; }
  .scroll td select, .scroll td input { flex: 1 1 10em; min-width: 0; width: auto; }
  .scroll td:last-child button { flex: 1; }
  .scroll td:last-child button + button { margin-left: 0; }
  .tabs { overflow-x: auto; flex-wrap: nowrap; max-width: 100%; }
  .tabs button { flex: 0 0 auto; }
  .modal { padding: 8px; }
  .modal .card { max-height: 94vh; }
}
</style>
</head>
<body>
<div id="scene" aria-hidden="true">
<svg viewBox="0 0 1440 900" preserveAspectRatio="xMidYMax slice" xmlns="http://www.w3.org/2000/svg" focusable="false">
  <defs>
    <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#070618"/><stop offset=".30" stop-color="#150f38"/>
      <stop offset=".52" stop-color="#3b1b52"/><stop offset=".66" stop-color="#8a3550"/>
      <stop offset=".76" stop-color="#d8643a"/><stop offset=".84" stop-color="#f3a444"/>
    </linearGradient>
    <radialGradient id="glow" cx="720" cy="640" r="620" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#ffd27a" stop-opacity=".95"/><stop offset=".18" stop-color="#ff9a4a" stop-opacity=".6"/>
      <stop offset=".5" stop-color="#d4503f" stop-opacity=".25"/><stop offset="1" stop-color="#d4503f" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="sun" cx=".5" cy=".5" r=".5">
      <stop offset="0" stop-color="#fff4cf"/><stop offset=".7" stop-color="#ffd27a"/><stop offset="1" stop-color="#ffb347"/>
    </radialGradient>
    <linearGradient id="mist" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#ffb27a" stop-opacity="0"/><stop offset=".5" stop-color="#ffb27a" stop-opacity=".22"/><stop offset="1" stop-color="#ffb27a" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="shade" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#05040f" stop-opacity="0"/><stop offset="1" stop-color="#05040f" stop-opacity=".55"/>
    </linearGradient>
  </defs>
  <rect width="1440" height="900" fill="url(#sky)"/>
  <g><circle cx="673" cy="85" r="1.4" fill="#fff" opacity="0.72" class="tw" style="animation-delay:-4.1s"/><circle cx="108" cy="45" r="0.7" fill="#fff" opacity="0.8"/><circle cx="758" cy="306" r="0.7" fill="#fff" opacity="0.23"/><circle cx="1049" cy="117" r="0.7" fill="#fff" opacity="0.65" class="tw" style="animation-delay:-0.5s"/><circle cx="898" cy="222" r="0.7" fill="#fff" opacity="0.42"/><circle cx="502" cy="54" r="1.4" fill="#fff" opacity="0.78"/><circle cx="131" cy="297" r="0.7" fill="#fff" opacity="0.25" class="tw" style="animation-delay:-6.0s"/><circle cx="467" cy="330" r="0.7" fill="#fff" opacity="0.18"/><circle cx="1191" cy="307" r="1.4" fill="#fff" opacity="0.23"/><circle cx="111" cy="121" r="0.7" fill="#fff" opacity="0.64" class="tw" style="animation-delay:-3.5s"/><circle cx="282" cy="156" r="1.4" fill="#fff" opacity="0.56"/><circle cx="305" cy="284" r="0.7" fill="#fff" opacity="0.28"/><circle cx="1179" cy="165" r="0.9" fill="#fff" opacity="0.54" class="tw" style="animation-delay:-0.6s"/><circle cx="1201" cy="300" r="0.9" fill="#fff" opacity="0.25"/><circle cx="772" cy="57" r="0.7" fill="#fff" opacity="0.78"/><circle cx="1165" cy="38" r="0.9" fill="#fff" opacity="0.82" class="tw" style="animation-delay:-3.1s"/><circle cx="1403" cy="280" r="1.4" fill="#fff" opacity="0.29"/><circle cx="653" cy="246" r="1.4" fill="#fff" opacity="0.37"/><circle cx="750" cy="161" r="0.9" fill="#fff" opacity="0.55" class="tw" style="animation-delay:-5.0s"/><circle cx="378" cy="365" r="0.9" fill="#fff" opacity="0.15"/><circle cx="177" cy="302" r="1.1" fill="#fff" opacity="0.24"/><circle cx="1085" cy="261" r="1.1" fill="#fff" opacity="0.33" class="tw" style="animation-delay:-4.6s"/><circle cx="929" cy="155" r="0.7" fill="#fff" opacity="0.56"/><circle cx="251" cy="270" r="1.4" fill="#fff" opacity="0.31"/><circle cx="347" cy="183" r="0.9" fill="#fff" opacity="0.5" class="tw" style="animation-delay:-5.9s"/><circle cx="1011" cy="223" r="0.7" fill="#fff" opacity="0.42"/><circle cx="1378" cy="47" r="1.1" fill="#fff" opacity="0.8"/><circle cx="706" cy="363" r="1.1" fill="#fff" opacity="0.15" class="tw" style="animation-delay:-3.8s"/><circle cx="1027" cy="304" r="1.4" fill="#fff" opacity="0.24"/><circle cx="150" cy="55" r="1.1" fill="#fff" opacity="0.78"/><circle cx="980" cy="364" r="0.7" fill="#fff" opacity="0.15" class="tw" style="animation-delay:-0.3s"/><circle cx="644" cy="339" r="1.4" fill="#fff" opacity="0.16"/><circle cx="592" cy="374" r="1.4" fill="#fff" opacity="0.15"/><circle cx="1379" cy="185" r="0.7" fill="#fff" opacity="0.5" class="tw" style="animation-delay:-6.0s"/><circle cx="955" cy="189" r="0.9" fill="#fff" opacity="0.49"/><circle cx="1261" cy="67" r="1.4" fill="#fff" opacity="0.75"/><circle cx="130" cy="119" r="1.1" fill="#fff" opacity="0.64" class="tw" style="animation-delay:-0.8s"/><circle cx="517" cy="211" r="1.4" fill="#fff" opacity="0.44"/><circle cx="1026" cy="49" r="0.9" fill="#fff" opacity="0.79"/><circle cx="929" cy="213" r="1.1" fill="#fff" opacity="0.44" class="tw" style="animation-delay:-5.6s"/><circle cx="290" cy="228" r="1.1" fill="#fff" opacity="0.4"/><circle cx="860" cy="191" r="1.4" fill="#fff" opacity="0.48"/><circle cx="482" cy="85" r="0.7" fill="#fff" opacity="0.72" class="tw" style="animation-delay:-1.1s"/><circle cx="319" cy="126" r="0.9" fill="#fff" opacity="0.63"/><circle cx="34" cy="256" r="0.9" fill="#fff" opacity="0.34"/><circle cx="548" cy="152" r="0.7" fill="#fff" opacity="0.57" class="tw" style="animation-delay:-0.9s"/><circle cx="868" cy="281" r="1.1" fill="#fff" opacity="0.29"/><circle cx="1258" cy="297" r="1.1" fill="#fff" opacity="0.25"/><circle cx="267" cy="361" r="0.7" fill="#fff" opacity="0.15" class="tw" style="animation-delay:-2.9s"/><circle cx="1403" cy="294" r="1.4" fill="#fff" opacity="0.26"/><circle cx="825" cy="212" r="1.4" fill="#fff" opacity="0.44"/><circle cx="222" cy="254" r="1.4" fill="#fff" opacity="0.35" class="tw" style="animation-delay:-0.3s"/><circle cx="400" cy="42" r="0.9" fill="#fff" opacity="0.81"/><circle cx="912" cy="91" r="0.7" fill="#fff" opacity="0.7"/><circle cx="706" cy="315" r="0.7" fill="#fff" opacity="0.22" class="tw" style="animation-delay:-0.6s"/><circle cx="10" cy="298" r="0.9" fill="#fff" opacity="0.25"/><circle cx="1108" cy="59" r="1.1" fill="#fff" opacity="0.77"/><circle cx="1266" cy="21" r="0.7" fill="#fff" opacity="0.85" class="tw" style="animation-delay:-5.5s"/><circle cx="435" cy="322" r="1.4" fill="#fff" opacity="0.2"/><circle cx="314" cy="332" r="1.1" fill="#fff" opacity="0.18"/><circle cx="721" cy="316" r="1.1" fill="#fff" opacity="0.21" class="tw" style="animation-delay:-3.0s"/><circle cx="261" cy="67" r="1.4" fill="#fff" opacity="0.75"/><circle cx="964" cy="253" r="1.4" fill="#fff" opacity="0.35"/><circle cx="648" cy="51" r="0.9" fill="#fff" opacity="0.79" class="tw" style="animation-delay:-0.6s"/><circle cx="711" cy="143" r="1.4" fill="#fff" opacity="0.59"/><circle cx="1427" cy="90" r="0.7" fill="#fff" opacity="0.7"/><circle cx="430" cy="278" r="1.1" fill="#fff" opacity="0.3" class="tw" style="animation-delay:-0.9s"/><circle cx="1423" cy="286" r="0.7" fill="#fff" opacity="0.28"/><circle cx="1091" cy="160" r="0.7" fill="#fff" opacity="0.55"/><circle cx="544" cy="273" r="1.1" fill="#fff" opacity="0.31" class="tw" style="animation-delay:-5.8s"/></g>
  <rect width="1440" height="900" fill="url(#glow)" class="pulse"/>
  <g class="sun"><circle cx="720" cy="640" r="74" fill="url(#sun)"/></g>
  <path d="M-40,625.7 L-20,623.8 L0,619.8 L20,614.9 L40,610.4 L60,607.2 L80,605.5 L100,604.8 L120,604.3 L140,603.0 L160,600.3 L180,596.1 L200,590.9 L220,585.9 L240,582.1 L260,580.5 L280,581.6 L300,584.9 L320,589.4 L340,593.8 L360,596.7 L380,597.0 L400,594.6 L420,589.8 L440,583.7 L460,577.4 L480,572.2 L500,568.4 L520,566.1 L540,564.7 L560,563.1 L580,560.6 L600,556.8 L620,551.8 L640,546.7 L660,542.5 L680,540.6 L700,542.0 L720,546.8 L740,554.4 L760,563.9 L780,573.6 L800,582.2 L820,588.8 L840,593.2 L860,596.0 L880,597.9 L900,599.9 L920,602.7 L940,606.5 L960,610.8 L980,614.5 L1000,616.6 L1020,616.2 L1040,613.2 L1060,608.0 L1080,601.7 L1100,595.7 L1120,591.3 L1140,589.5 L1160,590.4 L1180,593.4 L1200,597.5 L1220,601.3 L1240,603.7 L1260,604.3 L1280,603.1 L1300,600.9 L1320,598.5 L1340,596.9 L1360,596.5 L1380,597.2 L1400,598.1 L1420,598.2 L1440,596.4 L1460,591.8 L1480,584.6 L1500,920 L-40,920 Z" fill="#6b2f5a"/>
  <path d="M-40,645.7 L-20,646.4 L0,647.6 L20,648.4 L40,648.0 L60,646.2 L80,643.2 L100,639.6 L120,636.1 L140,633.8 L160,633.4 L180,635.0 L200,638.6 L220,643.5 L240,648.5 L260,652.5 L280,654.3 L300,653.2 L320,648.8 L340,641.5 L360,632.0 L380,621.5 L400,611.4 L420,602.7 L440,596.4 L460,592.6 L480,591.3 L500,591.8 L520,593.2 L540,594.7 L560,595.5 L580,595.6 L600,594.9 L620,594.2 L640,594.3 L660,596.1 L680,600.5 L700,607.8 L720,617.9 L740,630.0 L760,643.0 L780,655.7 L800,666.6 L820,674.8 L840,679.6 L860,681.2 L880,679.9 L900,676.8 L920,672.9 L940,669.4 L960,667.0 L980,666.1 L1000,666.4 L1020,667.5 L1040,668.5 L1060,668.6 L1080,667.1 L1100,663.7 L1120,658.8 L1140,653.1 L1160,647.4 L1180,643.0 L1200,640.8 L1220,641.3 L1240,644.7 L1260,650.5 L1280,657.7 L1300,665.1 L1320,671.3 L1340,675.2 L1360,676.2 L1380,674.1 L1400,669.4 L1420,662.8 L1440,655.3 L1460,648.1 L1480,641.9 L1500,920 L-40,920 Z" fill="#4a2552"/>
  <path d="M-40,693.7 L-20,691.6 L0,690.7 L20,691.1 L40,692.4 L60,694.1 L80,695.5 L100,695.7 L120,694.2 L140,690.5 L160,684.6 L180,676.7 L200,667.4 L220,657.6 L240,648.3 L260,640.5 L280,635.0 L300,632.4 L320,632.9 L340,636.2 L360,642.0 L380,649.3 L400,657.4 L420,665.4 L440,672.7 L460,678.8 L480,683.8 L500,687.8 L520,691.4 L540,695.0 L560,699.3 L580,704.7 L600,711.4 L620,719.4 L640,728.1 L660,736.8 L680,744.9 L700,751.3 L720,755.4 L740,756.7 L760,755.0 L780,750.5 L800,744.0 L820,736.1 L840,728.0 L860,720.5 L880,714.6 L900,710.8 L920,709.2 L940,709.8 L960,712.0 L980,715.1 L1000,718.4 L1020,721.2 L1040,722.8 L1060,723.1 L1080,722.0 L1100,719.8 L1120,717.2 L1140,714.8 L1160,713.1 L1180,712.7 L1200,713.8 L1220,716.2 L1240,719.5 L1260,723.0 L1280,725.9 L1300,727.3 L1320,726.5 L1340,722.9 L1360,716.6 L1380,707.7 L1400,696.9 L1420,685.1 L1440,673.2 L1460,662.3 L1480,653.2 L1500,920 L-40,920 Z" fill="#2c2048"/>
  <path d="M-40,725.0 L-20,719.1 L0,712.8 L20,706.7 L40,701.6 L60,698.0 L80,696.6 L100,697.8 L120,701.6 L140,707.9 L160,716.5 L180,726.7 L200,737.8 L220,749.1 L240,759.9 L260,769.6 L280,777.7 L300,784.2 L320,789.1 L340,792.5 L360,795.0 L380,796.9 L400,798.8 L420,801.0 L440,803.7 L460,806.9 L480,810.5 L500,814.2 L520,817.4 L540,819.7 L560,820.6 L580,819.6 L600,816.7 L620,811.9 L640,805.4 L660,797.7 L680,789.5 L700,781.4 L720,774.3 L740,768.7 L760,765.0 L780,763.6 L800,764.4 L820,767.1 L840,771.3 L860,776.3 L880,781.5 L900,786.2 L920,789.9 L940,792.2 L960,792.9 L980,792.2 L1000,790.2 L1020,787.5 L1040,784.4 L1060,781.5 L1080,779.1 L1100,777.4 L1120,776.5 L1140,776.1 L1160,776.0 L1180,775.6 L1200,774.5 L1220,772.1 L1240,768.1 L1260,762.2 L1280,754.5 L1300,745.2 L1320,734.8 L1340,724.1 L1360,713.6 L1380,704.3 L1400,696.7 L1420,691.4 L1440,688.7 L1460,688.7 L1480,691.1 L1500,920 L-40,920 Z" fill="#142a3a"/>
  <path d="M-40,823.8 L-20,833.4 L0,842.9 L20,851.8 L40,859.8 L60,866.3 L80,871.2 L100,874.3 L120,875.9 L140,875.9 L160,874.9 L180,873.1 L200,870.9 L220,868.8 L240,867.1 L260,865.9 L280,865.5 L300,865.6 L320,866.3 L340,867.1 L360,867.9 L380,868.3 L400,868.0 L420,866.7 L440,864.3 L460,860.8 L480,856.3 L500,851.1 L520,845.6 L540,840.2 L560,835.2 L580,831.2 L600,828.5 L620,827.3 L640,827.6 L660,829.5 L680,832.7 L700,836.8 L720,841.5 L740,846.2 L760,850.5 L780,853.9 L800,856.1 L820,856.8 L840,856.0 L860,853.7 L880,850.3 L900,845.8 L920,840.9 L940,835.8 L960,830.9 L980,826.5 L1000,822.8 L1020,820.0 L1040,817.9 L1060,816.3 L1080,815.1 L1100,813.9 L1120,812.4 L1140,810.3 L1160,807.3 L1180,803.3 L1200,798.4 L1220,792.7 L1240,786.5 L1260,780.2 L1280,774.2 L1300,769.0 L1320,765.1 L1340,762.8 L1360,762.3 L1380,763.7 L1400,767.1 L1420,772.2 L1440,778.6 L1460,785.9 L1480,793.7 L1500,920 L-40,920 Z" fill="#0a1c22"/>
  <g class="mist"><rect x="-200" y="640" width="1840" height="70" fill="url(#mist)"/></g>
  <g class="mist m2"><rect x="-200" y="720" width="1840" height="60" fill="url(#mist)"/></g>
  <rect y="640" width="1440" height="260" fill="url(#shade)"/>
</svg></div>
<header id="bar"></header>
<main id="app"></main>
<footer>Registration National prototype. Demo data only; no real NIDA or SMS integration.</footer>
<div id="toast" role="status" aria-live="polite"></div>
<script>
/* ===== geo.js: Rwanda provinces, districts, sectors and cells ===== */
/* Rwanda administrative divisions: 5 provinces, 30 districts, 416 sectors, 2,148 cells (Intara > Akarere > Umurenge > Akagari).
   Data source: the open-source "rwanda" package v3.0.4 (MIT licence, github.com/knowbee/rwanda), corrected against the
   NISR list of administrative units (Masaka cells in Kicukiro, duplicate Mahama cell, Mageragere and Ndoranyi spellings).
   Sector names are NOT unique nationally (for example Remera is in four districts), so a sector is always identified by District + Sector. */
const GEO = {
  "East": {
    "Bugesera": {
      "Gashora": ["Biryogo", "Kabuye", "Kagomasi", "Mwendo", "Ramiro"],
      "Juru": ["Juru", "Kabukuba", "Mugorore", "Musovu", "Rwinume"],
      "Kamabuye": ["Biharagu", "Burenge", "Kampeka", "Nyakayaga", "Tunda"],
      "Mareba": ["Bushenyi", "Gakomeye", "Nyamigina", "Rango", "Rugarama"],
      "Mayange": ["Gakamba", "Kagenge", "Kibenga", "Kibirizi", "Mbyo"],
      "Musenyi": ["Gicaca", "Musenyi", "Nyagihunika", "Rulindo"],
      "Mwogo": ["Bitaba", "Kagasa", "Rugunga", "Rurenge"],
      "Ngeruka": ["Gihembe", "Murama", "Ngeruka", "Nyakayenzi", "Rutonde"],
      "Ntarama": ["Cyugaro", "Kanzenze", "Kibungo"],
      "Nyamata": ["Kanazi", "Kayumba", "Maranyundo", "Murama", "Nyamata y'Umujyi"],
      "Nyarugenge": ["Gihinga", "Kabuye", "Murambi", "Ngenda", "Rugando"],
      "Rilima": ["Kabeza", "Karera", "Kimaranzara", "Ntarama", "Nyabagendwa"],
      "Ruhuha": ["Bihari", "Gatanga", "Gikundamvura", "Kindama", "Ruhuha"],
      "Rweru": ["Batima", "Kintambwe", "Mazane", "Nemba", "Nkanga", "Sharita"],
      "Shyara": ["Kabagugu", "Kamabuye", "Nziranziza", "Rebero", "Rutare"]
    },
    "Gatsibo": {
      "Gasange": ["Kigabiro", "Kimana", "Teme", "Viro"],
      "Gatsibo": ["Gatsibo", "Manishya", "Mugera", "Nyabicwamba", "Nyagahanga"],
      "Gitoki": ["Bukomane", "Cyabusheshe", "Karubungo", "Mpondwa", "Nyamirama", "Rubira"],
      "Kabarore": ["Kabarore", "Kabeza", "Karenge", "Marimba", "Nyabikiri", "Simbwa"],
      "Kageyo": ["Busetsa", "Gituza", "Kintu", "Nyagisozi"],
      "Kiramuruzi": ["Akabuga", "Gakenke", "Gakoni", "Nyabisindu"],
      "Kiziguro": ["Agakomeye", "Mbogo", "Ndatemwa", "Rubona"],
      "Muhura": ["Bibare", "Gakorokombe", "Mamfu", "Rumuli", "Taba"],
      "Murambi": ["Murambi", "Nyamiyaga", "Rwankuba", "Rwimitereri"],
      "Ngarama": ["Bugamba", "Karambi", "Kigasha", "Ngarama", "Nyarubungo"],
      "Nyagihanga": ["Gitinda", "Kibare", "Mayange", "Murambi", "Nyagitabire", "Nyamirama"],
      "Remera": ["Bushobora", "Butiruka", "Kigabiro", "Nyagakombe", "Rurenge", "Rwarenga"],
      "Rugarama": ["Bugarama", "Gihuta", "Kanyangese", "Matare", "Matunguru", "Remera"],
      "Rwimbogo": ["Kiburara", "Munini", "Nyamatete", "Rwikiniro"]
    },
    "Kayonza": {
      "Gahini": ["Juru", "Kahi", "Kiyenzi", "Urugarama"],
      "Kabare": ["Cyarubare", "Gitara", "Kirehe", "Rubimba", "Rubumba"],
      "Kabarondo": ["Cyabajwa", "Cyinzovu", "Kabura", "Rusera"],
      "Mukarange": ["Bwiza", "Kayonza", "Mburabuturo", "Nyagatovu", "Rugendabari"],
      "Murama": ["Bunyentongo", "Muko", "Murama", "Nyakanazi", "Rusave"],
      "Murundi": ["Buhabwa", "Karambi", "Murundi", "Ryamanyoni"],
      "Mwiri": ["Kageyo", "Migera", "Nyamugari", "Nyawera"],
      "Ndego": ["Byimana", "Isangano", "Karambi", "Kiyovu"],
      "Nyamirama": ["Gikaya", "Musumba", "Rurambi", "Shyogo"],
      "Rukara": ["Kawangire", "Rukara", "Rwimishinya"],
      "Ruramira": ["Bugambira", "Nkamba", "Ruyonza", "Umubuga"],
      "Rwinkwavu": ["Gihinga", "Mbarara", "Mukoyoyo", "Nkondo"]
    },
    "Kirehe": {
      "Gahara": ["Butezi", "Muhamba", "Murehe", "Nyagasenyi", "Nyakagezi", "Rubimba"],
      "Gatore": ["Curazo", "Cyunuzi", "Muganza", "Nyamiryango", "Rwabutazi", "Rwantonde"],
      "Kigarama": ["Cyanya", "Kigarama", "Kiremera", "Nyakerera", "Nyankurazo"],
      "Kigina": ["Gatarama", "Rugarama", "Ruhanga", "Rwanteru"],
      "Kirehe": ["Gahama", "Kirehe", "Nyabigega", "Nyabikokora", "Rwesero"],
      "Mahama": ["Kamombo", "Munini", "Mwoga", "Saruhembe"],
      "Mpanga": ["Bwiyorere", "Kankobwa", "Mpanga", "Mushongi", "Nasho", "Nyakabungo", "Rubaya"],
      "Musaza": ["Gasarabwayi", "Kabuga", "Mubuga", "Musaza", "Nganda"],
      "Mushikiri": ["Bisagara", "Cyamigurwa", "Rugarama", "Rwanyamuhanga", "Rwayikona"],
      "Nasho": ["Cyambwe", "Kagese", "Ntaruka", "Rubirizi", "Rugoma"],
      "Nyamugari": ["Bukora", "Kagasa", "Kazizi", "Kiyanzi", "Nyamugari"],
      "Nyarubuye": ["Mareba", "Nyabitare", "Nyarutunga"]
    },
    "Ngoma": {
      "Gashanda": ["Cyerwa", "Giseri", "Munege", "Mutsindo"],
      "Jarama": ["Ihanika", "Jarama", "Karenge", "Kibimba", "Kigoma"],
      "Karembo": ["Akaziba", "Karaba", "Nyamirambo"],
      "Kazo": ["Birenga", "Gahurire", "Karama", "Kinyonzo", "Umukamba"],
      "Kibungo": ["Cyasemakamba", "Gahima", "Gatonde", "Karenge", "Mahango"],
      "Mugesera": ["Akabungo", "Mugatare", "Ntanga", "Nyamugari", "Nyange"],
      "Murama": ["Gitaraga", "Kigabiro", "Mvumba", "Rurenge", "Sakara"],
      "Mutenderi": ["Karwema", "Kibare", "Mutenderi", "Muzingira", "Nyagasozi"],
      "Remera": ["Bugera", "Kinunga", "Ndekwe", "Nyamagana"],
      "Rukira": ["Buliba", "Kibatsi", "Nyaruvumu", "Nyinya"],
      "Rukumberi": ["Gituza", "Ntovi", "Rubago", "Rubona", "Rwintashya"],
      "Rurenge": ["Akagarama", "Muhurire", "Musya", "Rugese", "Rujambara", "Rwikubo"],
      "Sake": ["Gafunzo", "Kibonde", "Nkanga", "Rukoma"],
      "Zaza": ["Nyagasozi", "Nyagatugunda", "Ruhembe", "Ruhinga"]
    },
    "Nyagatare": {
      "Gatunda": ["Cyagaju", "Kabeza", "Nyamikamba", "Nyamirembe", "Nyangara", "Nyarurema", "Rwensheke"],
      "Karama": ["Bushara", "Cyenkwanzi", "Gikagati", "Gikundamvura", "Kabuga", "Ndego", "Nyakiga"],
      "Karangazi": ["Kamate", "Karama", "Kizirakome", "Mbare", "Musenyi", "Ndama", "Nyagashanga", "Nyamirama", "Rubagabaga", "Rwenyemera", "Rwisirabo"],
      "Katabagemu": ["Bayigaburire", "Kaduha", "Kanyeganyege", "Katabagemu", "Kigarama", "Nyakigando", "Rubira", "Rugazi", "Rutoma"],
      "Kiyombe": ["Gataba", "Gitenga", "Kabungo", "Karambo", "Karujumba", "Tovu"],
      "Matimba": ["Bwera", "Byimana", "Cyembogo", "Kagitumba", "Kanyonza", "Matimba", "Nyabwishongwezi", "Rwentanga"],
      "Mimuri": ["Bibare", "Gakoma", "Mahoro", "Mimuri", "Rugari"],
      "Mukama": ["Bufunda", "Gatete", "Gihengeri", "Gishororo", "Kagina", "Rugarama"],
      "Musheri": ["Kibirizi", "Kijojo", "Musheri", "Ntoma", "Nyagatabire", "Nyamiyonga", "RugaramaI", "RugaramaII"],
      "Nyagatare": ["Barija", "Bushoga", "Cyabayaga", "Gakirage", "Kamagiri", "Nsheke", "Nyagatare", "Rutaraka", "Ryabega"],
      "Rukomo": ["Gahurura", "Gashenyi", "Nyakagarama", "Rukomo II", "Rurenge"],
      "Rwempasha": ["Cyenjonjo", "Gasinga", "Kabare", "Kazaza", "Mishenyi", "Rugarama", "Rukorota", "Rutare", "Rwempasha", "Ryeru"],
      "Rwimiyaga": ["Gacundezi", "Kabeza", "Kirebe", "Ntoma", "Nyarupfubire", "Nyendo", "Rutungu", "Rwimiyaga"],
      "Tabagwe": ["Gishuro", "Gitengure", "Nkoma", "Nyabitekeri", "Nyagatoma", "Shonga", "Tabagwe"]
    },
    "Rwamagana": {
      "Fumbwe": ["Mununu", "Nyagasambu", "Nyakagunga", "Nyamirama", "Nyarubuye", "Sasabirago"],
      "Gahengeri": ["Gihumuza", "Kagezi", "Kanyangese", "Kibare", "Mutamwa", "Rugarama", "Runyinya", "Rweri"],
      "Gishali": ["Binunga", "Bwinsanga", "Cyinyana", "Gati", "Kavumu", "Ruhimbi", "Ruhunda"],
      "Karenge": ["Bicaca", "Byimana", "Kabasore", "Kangamba", "Karenge", "Nyabubare", "Nyamatete"],
      "Kigabiro": ["Bwiza", "Cyanya", "Nyagasenyi", "Sibagire", "Sovu"],
      "Muhazi": ["Byeza", "Kabare", "Karambi", "Karitutu", "Kitazigurwa", "Murambi", "Nsinda", "Ntebe", "Nyarusange"],
      "Munyaga": ["Kaduha", "Nkungu", "Rweru", "Zinga"],
      "Munyiginya": ["Binunga", "Bwana", "Cyarukamba", "Cyimbazi", "Nkomangwa", "Nyarubuye"],
      "Musha": ["Akabare", "Budahanda", "Kagarama", "Musha", "Nyabisindu", "Nyakabanda"],
      "Muyumbu": ["Akinyambo", "Bujyujyu", "Murehe", "Ntebe", "Nyarukombe"],
      "Mwulire": ["Bicumbi", "Bushenyi", "Mwulire", "Ntunga"],
      "Nyakaliro": ["Bihembe", "Gatare", "Gishore", "Munini", "Rwimbogo"],
      "Nzige": ["Akanzu", "Kigarama", "Murama", "Rugarama"],
      "Rubona": ["Byinza", "Kabatasi", "Kabuye", "Karambi", "Mabare", "Nawe"]
    }
  },
  "Kigali": {
    "Gasabo": {
      "Bumbogo": ["Kinyaga", "Musave", "Mvuzo", "Ngara", "Nkuzuzu", "Nyabikenke", "Nyagasozi"],
      "Gatsata": ["Karuruma", "Nyamabuye", "Nyamugari"],
      "Gikomero": ["Gasagara", "Gicaca", "Kibara", "Munini", "Murambi"],
      "Gisozi": ["Musezero", "Ruhango"],
      "Jabana": ["Akamatamu", "Bweramvura", "Kabuye", "Kidashya", "Ngiryi"],
      "Jali": ["Agateko", "Buhiza", "Muko", "Nkusi", "Nyabuliba", "Nyakabungo", "Nyamitanga"],
      "Kacyiru": ["Kamatamu", "Kamutwa", "Kibaza"],
      "Kimihurura": ["Kamukina", "Kimihurura", "Rugando"],
      "Kimironko": ["Bibare", "Kibagabaga", "Nyagatovu"],
      "Kinyinya": ["Gacuriro", "Gasharu", "Kagugu", "Murama"],
      "Ndera": ["Bwiza", "Cyaruzinge", "Kibenga", "Masoro", "Mukuyu", "Rudashya"],
      "Nduba": ["Butare", "Gasanze", "Gasura", "Gatunga", "Muremure", "Sha", "Shango"],
      "Remera": ["Nyabisindu", "Nyarutarama", "Rukiri I", "Rukiri II"],
      "Rusororo": ["Bisenga", "Gasagara", "Kabuga I", "Kabuga II", "Kinyana", "Mbandazi", "Nyagahinga", "Ruhanga"],
      "Rutunga": ["Gasabo", "Indatemwa", "Kabaliza", "Kacyatwa", "Kibenga", "Kigabiro"]
    },
    "Kicukiro": {
      "Gahanga": ["Gahanga", "Kagasa", "Karembure", "Murinja", "Nunga", "Rwabutenge"],
      "Gatenga": ["Gatenga", "Karambo", "Nyanza", "Nyarurama"],
      "Gikondo": ["Kagunga", "Kanserege", "Kinunga"],
      "Kagarama": ["Kanserege", "Muyange", "Rukatsa"],
      "Kanombe": ["Busanza", "Kabeza", "Karama", "Rubirizi"],
      "Kicukiro": ["Gasharu", "Kagina", "Kicukiro", "Ngoma"],
      "Kigarama": ["Bwerankori", "Karugira", "Kigarama", "Nyarurama", "Rwampara"],
      "Masaka": ["Ayabaraya", "Cyimo", "Gako", "Gitaraga", "Mbabe", "Rusheshe"],
      "Niboye": ["Gatare", "Niboye", "Nyakabanda"],
      "Nyarugunga": ["Kamashashi", "Nonko", "Rwimbogo"]
    },
    "Nyarugenge": {
      "Gitega": ["Akabahizi", "Akabeza", "Gacyamo", "Kigarama", "Kinyange", "Kora"],
      "Kanyinya": ["Nyamweru", "Nzove", "Taba"],
      "Kigali": ["Kigali", "Mwendo", "Nyabugogo", "Ruriba", "Rwesero"],
      "Kimisagara": ["Kamuhoza", "Katabaro", "Kimisagara"],
      "Mageragere": ["Kankuba", "Kavumu", "Mataba", "Ntungamo", "Nyarufunzo", "Nyarurenzi", "Runzenze"],
      "Muhima": ["Amahoro", "Kabasengerezi", "Kabeza", "Nyabugogo", "Rugenge", "Tetero", "Ubumwe"],
      "Nyakabanda": ["Munanira I", "Munanira II", "Nyakabanda I", "Nyakabanda II"],
      "Nyamirambo": ["Cyivugiza", "Gasharu", "Mumena", "Rugarama"],
      "Nyarugenge": ["Agatare", "Biryogo", "Kiyovu", "Rwampara"],
      "Rwezamenyo": ["Kabuguru I", "Kabuguru II", "Rwezamenyo I", "Rwezamenyo II"]
    }
  },
  "North": {
    "Burera": {
      "Bungwe": ["Bungwe", "Bushenya", "Mudugari", "Tumba"],
      "Butaro": ["Gatsibo", "Mubuga", "Muhotora", "Nyamicucu", "Rusumo"],
      "Cyanika": ["Gasiza", "Gisovu", "Kabyiniro", "Kagitega", "Kamanyana", "Nyagahinga"],
      "Cyeru": ["Butare", "Ndongozi", "Ruyange"],
      "Gahunga": ["Buramba", "Gisizi", "Kidakama", "Nyangwe", "Rwasa"],
      "Gatebe": ["Gabiro", "Musenda", "Rwambogo", "Rwasa"],
      "Gitovu": ["Mariba", "Musasa", "Runoga"],
      "Kagogo": ["Kabaya", "Kayenzi", "Kiringa", "Nyamabuye"],
      "Kinoni": ["Gafuka", "Nkenke", "Nkumba", "Ntaruka"],
      "Kinyababa": ["Bugamba", "Kaganda", "Musasa", "Rutovu"],
      "Kivuye": ["Bukwashuri", "Gashanje", "Murwa", "Nyirataba"],
      "Nemba": ["Kivumu", "Nyamugari", "Rubona", "Rushara"],
      "Rugarama": ["Cyahi", "Gafumba", "Karangara", "Rurembo"],
      "Rugengabari": ["Kilibata", "Mucaca", "Nyanamo", "Rukandabyuma"],
      "Ruhunde": ["Gaseke", "Gatare", "Gitovu", "Rusekera"],
      "Rusarabuye": ["Kabona", "Ndago", "Ruhanga"],
      "Rwerere": ["Gacundura", "Gashoro", "Ruconsho", "Rugari"]
    },
    "Gakenke": {
      "Busengo": ["Birambo", "Butereri", "Byibuhiro", "Kamina", "Kirabo", "Mwumba", "Ruhanga"],
      "Coko": ["Kiruku", "Mbirima", "Nyange", "Nyanza"],
      "Cyabingo": ["Muhaza", "Muhororo", "Muramba", "Mutanda", "Rukore"],
      "Gakenke": ["Buheta", "Kagoma", "Nganzo", "Rusagara"],
      "Gashenyi": ["Nyacyina", "Rukura", "Rutabo", "Rutenderi", "Taba"],
      "Janja": ["Gakindo", "Gashyamba", "Gatwa", "Karukungu"],
      "Kamubuga": ["Kamubuga", "Kidomo", "Mbatabata", "Rukore"],
      "Karambo": ["Kanyanza", "Karambo", "Kirebe"],
      "Kivuruga": ["Cyintare", "Gasiza", "Rugimbu", "Ruhinga", "Sereri"],
      "Mataba": ["Buyange", "Gikombe", "Nyundo"],
      "Minazi": ["Gasiho", "Munyana", "Murambi", "Raba"],
      "Mugunga": ["Gahinga", "Munyana", "Mutego", "Nkomane", "Rutabo", "Rutenderi", "Rwamambe"],
      "Muhondo": ["Busake", "Bwenda", "Gasiza", "Gihinga", "Huro", "Musagara", "Musenyi", "Ruganda", "Rwinkuba"],
      "Muyongwe": ["Bumba", "Gisiza", "Karyango", "Nganzo", "Va"],
      "Muzo": ["Kabatezi", "Kiryamo", "Mubuga", "Mwiyando", "Rwa"],
      "Nemba": ["Buranga", "Gahinga", "Gisozi", "Mucaca"],
      "Ruli": ["Busoro", "Gikingo", "Jango", "Ruli", "Rwesero"],
      "Rusasa": ["Gataba", "Kamonyi", "Murambi", "Nyundo", "Rumbi", "Rurembo"],
      "Rushashi": ["Burimba", "Busanane", "Joma", "Kageyo", "Mbogo", "Razi", "Rwankuba", "Shyombwe"]
    },
    "Gicumbi": {
      "Bukure": ["Karenge", "Kigabiro", "Kivumu", "Rwesero"],
      "Bwisige": ["Bwisige", "Gihuke", "Mukono", "Nyabushingitwa"],
      "Byumba": ["Gacurabwenge", "Gisuna", "Kibali", "Kivugiza", "Murama", "Ngondore", "Nyakabungo", "Nyamabuye", "Nyarutarama"],
      "Cyumba": ["Gasunzu", "Muhambo", "Nyakabungo", "Nyambare", "Nyaruka", "Rwankonjo"],
      "Giti": ["Gatobotobo", "Murehe", "Tanda"],
      "Kageyo": ["Gihembe", "Horezo", "Kabuga", "Muhondo", "Nyamiyaga"],
      "Kaniga": ["Bugomba", "Gatoma", "Mulindi", "Nyarwambu", "Rukurura"],
      "Manyagiro": ["Kabuga", "Nyiragifumba", "Nyiravugiza", "Remera", "Rusekera", "Ryaruyumba"],
      "Miyove": ["Gakenke", "Miyove", "Mubuga"],
      "Mukarange": ["Cyamuganga", "Gatenga", "Kiruhura", "Mutarama", "Rugerero", "Rusambya"],
      "Muko": ["Cyamuhinda", "Kigoma", "Mwendo", "Ngange", "Rebero"],
      "Mutete": ["Gaseke", "Kabeza", "Musenyi", "Mutandi", "Nyarubuye"],
      "Nyamiyaga": ["Gahumuliza", "Jamba", "Kabeza", "Kabuga", "Karambo", "Kiziba", "Mataba"],
      "Nyankenke": ["Butare", "Kigogo", "Kinishya", "Rusasa", "Rutete", "Rwagihura", "Yaramba"],
      "Rubaya": ["Gihanga", "Gishambashayo", "Gishari", "Muguramo", "Nyamiyaga"],
      "Rukomo": ["Cyeya", "Cyuru", "Gisiza", "Kinyami", "Mabare", "Munyinya"],
      "Rushaki": ["Gitega", "Kamutora", "Karurama"],
      "Rutare": ["Bikumba", "Gasharu", "Gatwaro", "Kigabiro", "Munanira", "Nkoto"],
      "Ruvune": ["Cyandaro", "Gasambya", "Gashirira", "Kabare", "Rebero", "Ruhondo"],
      "Rwamiko": ["Cyeru", "Kigabiro", "Nyagahinga"],
      "Shangasha": ["Bushara", "Kitazigurwa", "Nyabishambi", "Nyabubare", "Shangasha"]
    },
    "Musanze": {
      "Busogo": ["Gisesero", "Kavumu", "Nyagisozi", "Sahara"],
      "Cyuve": ["Bukinanyana", "Buruba", "Cyanya", "Kabeza", "Migeshi", "Rwebeya"],
      "Gacaca": ["Gakoro", "Gasakuza", "Kabirizi", "Karwasa"],
      "Gashaki": ["Kigabiro", "Kivumu", "Mbwe", "Muharuro"],
      "Gataraga": ["Mudakama", "Murago", "Rubindi", "Rungu"],
      "Kimonyi": ["Birira", "Buramira", "Kivumu", "Mbizi"],
      "Kinigi": ["Bisoke", "Kaguhu", "Kampanga", "Nyabigoma", "Nyonirima"],
      "Muhoza": ["Cyabararika", "Kigombe", "Mpenge", "Ruhengeri"],
      "Muko": ["Cyivugiza", "Cyogo", "Mburabuturo", "Songa"],
      "Musanze": ["Cyabagarura", "Garuka", "Kabazungu", "Nyarubuye", "Rwambogo"],
      "Nkotsi": ["Bikara", "Gashinga", "Mubago", "Rugeshi", "Ruyumba"],
      "Nyange": ["Cyivugiza", "Kabeza", "Kamwumba", "Muhabura", "Ninda"],
      "Remera": ["Gasongero", "Kamisave", "Murandi", "Murwa", "Rurambo"],
      "Rwaza": ["Bumara", "Kabushinge", "Musezero", "Nturo", "Nyarubuye"],
      "Shingiro": ["Gakingo", "Kibuguzo", "Mudende", "Mugari"]
    },
    "Rulindo": {
      "Base": ["Cyohoha", "Gitare", "Rwamahwa"],
      "Burega": ["Butangampundu", "Karengeri", "Taba"],
      "Bushoki": ["Gasiza", "Giko", "Kayenzi", "Mukoto", "Nyirangarama"],
      "Buyoga": ["Busoro", "Butare", "Gahororo", "Gitumba", "Karama", "Mwumba", "Ndarage"],
      "Cyinzuzi": ["Budakiranya", "Migendezo", "Rudogo"],
      "Cyungo": ["Burehe", "Marembo", "Rwili"],
      "Kinihira": ["Butunzi", "Karegamazi", "Marembo", "Rebero"],
      "Kisaro": ["Gitatsa", "Kamushenyi", "Kigarama", "Mubuga", "Murama", "Sayo"],
      "Masoro": ["Kabuga", "Kigarama", "Kivugiza", "Nyamyumba", "Shengampuli"],
      "Mbogo": ["Bukoro", "Mushari", "Ngiramazi", "Rurenge"],
      "Murambi": ["Bubangu", "Gatwa", "Mugambazi", "Mvuzo"],
      "Ngoma": ["Kabuga", "Karambo", "Mugote", "Munyarwanda"],
      "Ntarabana": ["Kajevuba", "Kiyanza", "Mahaza"],
      "Rukozo": ["Buraro", "Bwimo", "Mberuka", "Mbuye"],
      "Rusiga": ["Gako", "Kirenge", "Taba"],
      "Shyorongi": ["Bugaragara", "Kijabagwe", "Muvumu", "Rubona", "Rutonde"],
      "Tumba": ["Barari", "Gahabwa", "Misezero", "Nyirabirori", "Taba"]
    }
  },
  "South": {
    "Gisagara": {
      "Gikonko": ["Cyiri", "Gasagara", "Gikonko", "Mbogo"],
      "Gishubi": ["Gabiro", "Nyabitare", "Nyakibungo", "Nyeranzi"],
      "Kansi": ["Akaboti", "Bwiza", "Sabusaro", "Umunini"],
      "Kibirizi": ["Duwani", "Kibirizi", "Muyira", "Ruturo"],
      "Kigembe": ["Agahabwa", "Gatovu", "Impinga", "Nyabikenke", "Rubona", "Rusagara"],
      "Mamba": ["Gakoma", "Kabumbwe", "Mamba", "Muyaga", "Ramba"],
      "Muganza": ["Cyumba", "Muganza", "Remera", "Rwamiko", "Saga"],
      "Mugombwa": ["Baziro", "Kibayi", "Kibu", "Mugombwa", "Mukomacara"],
      "Mukindo": ["Gitega", "Mukiza", "Nyabisagara", "Runyinya"],
      "Musha": ["Bukinanyana", "Gatovu", "Kigarama", "Kimana"],
      "Ndora": ["Bweya", "Cyamukuza", "Dahwe", "Gisagara", "Mukande"],
      "Nyanza": ["Higiro", "Nyamugari", "Nyaruteja", "Umubanga"],
      "Save": ["Gatoki", "Munazi", "Rwanza", "Shyanda", "Zivu"]
    },
    "Huye": {
      "Gishamvu": ["Nyakibanda", "Nyumba", "Ryakibogo", "Shori"],
      "Huye": ["Muyogoro", "Nyakagezi", "Rukira", "Sovu"],
      "Karama": ["Buhoro", "Bunazi", "Gahororo", "Kibingo", "Muhembe"],
      "Kigoma": ["Gishihe", "Kabatwa", "Kabuga", "Karambi", "Musebeya", "Nyabisindu", "Rugarama", "Shanga"],
      "Kinazi": ["Byinza", "Gahana", "Gitovu", "Kabona", "Sazange"],
      "Maraba": ["Buremera", "Gasumba", "Kabuye", "Kanyinya", "Shanga", "Shyembe"],
      "Mbazi": ["Gatobotobo", "Kabuga", "Mutunda", "Mwulire", "Rugango", "Rusagara", "Tare"],
      "Mukura": ["Bukomeye", "Buvumu", "Icyeru", "Rango A"],
      "Ngoma": ["Butare", "Kaburemera", "Matyazo", "Ngoma"],
      "Ruhashya": ["Busheshi", "Gatovu", "Karama", "Mara", "Muhororo", "Rugogwe", "Ruhashya"],
      "Rusatira": ["Buhimba", "Gafumba", "Kimirehe", "Kimuna", "Kiruhura", "Mugogwe"],
      "Rwaniro": ["Gatwaro", "Kamwambi", "Kibiraro", "Mwendo", "Nyamabuye", "Nyaruhombo", "Shyunga"],
      "Simbi": ["Cyendajuru", "Gisakura", "Kabusanza", "Mugobore", "Nyangazi"],
      "Tumba": ["Cyarwa", "Cyimana", "Gitwa", "Mpare", "Rango B"]
    },
    "Kamonyi": {
      "Gacurabwenge": ["Gihinga", "Gihira", "Kigembe", "Nkingo"],
      "Karama": ["Bitare", "Bunyonga", "Muganza", "Nyamirembe"],
      "Kayenzi": ["Bugarama", "Cubi", "Kayonza", "Kirwa", "Mataba", "Nyamirama"],
      "Kayumbu": ["Busoro", "Gaseke", "Giko", "Muyange"],
      "Mugina": ["Jenda", "Kabugondo", "Mbati", "Mugina", "Nteko"],
      "Musambira": ["Buhoro", "Cyambwe", "Karengera", "Kivumu", "Mpushi", "Rukambura"],
      "Ngamba": ["Kabuga", "Kazirabonde", "Marembo"],
      "Nyamiyaga": ["Bibungo", "Kabashumba", "Kidahwe", "Mukinga", "Ngoma"],
      "Nyarubaka": ["Gitare", "Kambyeyi", "Kigusa", "Nyagishubi", "Ruyanza"],
      "Rugarika": ["Bihembe", "Kigese", "Masaka", "Nyarubuye", "Sheli"],
      "Rukoma": ["Bugoba", "Buguri", "Gishyeshye", "Murehe", "Mwirute", "Remera", "Taba"],
      "Runda": ["Gihara", "Kabagesera", "Kagina", "Muganza", "Ruyenzi"]
    },
    "Muhanga": {
      "Cyeza": ["Biringaga", "Kigarama", "Kivumu", "Makera", "Nyarunyinya", "Shori"],
      "Kabacuzi": ["Buramba", "Butare", "Kabuye", "Kavumu", "Kibyimba", "Ngarama", "Ngoma", "Sholi"],
      "Kibangu": ["Gisharu", "Gitega", "Jurwe", "Mubuga", "Rubyiniro", "Ryakanimba"],
      "Kiyumba": ["Budende", "Ndago", "Remera", "Ruhina", "Rukeri"],
      "Muhanga": ["Kanyinya", "Nganzo", "Nyamirama", "Remera", "Tyazo"],
      "Mushishiro": ["Matyazo", "Munazi", "Nyagasozi", "Rukaragata", "Rwasare", "Rwigerero"],
      "Nyabinoni": ["Gashorera", "Masangano", "Mbuga", "Muvumba", "Nyarusozi"],
      "Nyamabuye": ["Gahogo", "Gifumba", "Gitarama", "Remera"],
      "Nyarusange": ["Mbiriri", "Musongati", "Ngaru", "Rusovu"],
      "Rongi": ["Gasagara", "Gasharu", "Karambo", "Nyamirambo", "Ruhango"],
      "Rugendabari": ["Gasave", "Kanyana", "Kibaga", "Mpinga", "Nsanga"],
      "Shyogwe": ["Kinini", "Mbare", "Mubuga", "Ruli"]
    },
    "Nyamagabe": {
      "Buruhukiro": ["Bushigishigi", "Byimana", "Gifurwe", "Kizimyamuriro", "Munini", "Rambya"],
      "Cyanika": ["Gitega", "Karama", "Kiyumba", "Ngoma", "Nyanza", "Nyanzoga"],
      "Gasaka": ["Kigeme", "Ngiryi", "Nyabivumu", "Nyamugari", "Nzega", "Remera"],
      "Gatare": ["Bakopfu", "Gatare", "Mukongoro", "Ruganda", "Shyeru"],
      "Kaduha": ["Kavumu", "Murambi", "Musenyi", "Nyabisindu", "Nyamiyaga"],
      "Kamegeri": ["Bwama", "Kamegeri", "Kirehe", "Kizi", "Nyarusiza", "Rususa"],
      "Kibirizi": ["Bugarama", "Bugarura", "Gashiha", "Karambo", "Ruhunga", "Uwindekezi"],
      "Kibumbwe": ["Bwenda", "Gakanka", "Kibibi", "Nyakiza"],
      "Kitabi": ["Kagano", "Mujuga", "Mukungu", "Shaba", "Uwingugu"],
      "Mbazi": ["Manwari", "Mutiwingoma", "Ngambi", "Ngara"],
      "Mugano": ["Gitondorero", "Gitwa", "Ruhinga", "Sovu", "Suti", "Yonde"],
      "Musange": ["Gasave", "Jenda", "Masagara", "Masangano", "Masizi", "Nyagisozi"],
      "Musebeya": ["Gatovu", "Nyarurambi", "Rugano", "Runege", "Rusekera", "Sekera"],
      "Mushubi": ["Buteteri", "Cyobe", "Gashwati"],
      "Nkomane": ["Bitandara", "Musaraba", "Mutengeri", "Nkomane", "Nyarwungo", "Twiya"],
      "Tare": ["Buhoro", "Gasarenda", "Gatovu", "Kaganza", "Nkumbure", "Nyamigina"],
      "Uwinkingi": ["Bigumira", "Gahira", "Kibyagira", "Mudasomwa", "Munyege", "Rugogwe"]
    },
    "Nyanza": {
      "Busasamana": ["Gahondo", "Kavumu", "Kibinja", "Nyanza", "Rwesero"],
      "Busoro": ["Gitovu", "Kimirama", "Masangano", "Munyinya", "Rukingiro", "Shyira"],
      "Cyabakamyi": ["Kadaho", "Karama", "Nyabinyenga", "Nyarurama", "Rubona"],
      "Kibilizi": ["Cyeru", "Mbuye", "Mututu", "Rwotso"],
      "Kigoma": ["Butansinda", "Butara", "Gahombo", "Gasoro", "Mulinja"],
      "Mukingo": ["Cyerezo", "Gatagara", "Kiruli", "Mpanga", "Ngwa", "Nkomero"],
      "Muyira": ["Gati", "Migina", "Nyamiyaga", "Nyamure", "Nyundo"],
      "Ntyazo": ["Bugali", "Cyotamakara", "Kagunga", "Katarara"],
      "Nyagisozi": ["Gahunga", "Kabirizi", "Kabuga", "Kirambi", "Rurangazi"],
      "Rwabicuma": ["Gacu", "Gishike", "Mubuga", "Mushirarungu", "Nyarusange", "Runga"]
    },
    "Nyaruguru": {
      "Busanze": ["Kirarangombe", "Nkanda", "Nteko", "Runyombyi", "Shororo"],
      "Cyahinda": ["Coko", "Cyahinda", "Gasasa", "Muhambara", "Rutobwe"],
      "Kibeho": ["Gakoma", "Kibeho", "Mbasa", "Mpanda", "Mubuga", "Nyange"],
      "Kivu": ["Cyanyirankora", "Gahurizo", "Kimina", "Kivu", "Rugerero"],
      "Mata": ["Gorwe", "Murambi", "Nyamabuye", "Ramba", "Rwamiko"],
      "Muganza": ["Muganza", "Rukore", "Samiyonga", "Uwacyiza"],
      "Munini": ["Giheta", "Ngarurira", "Ngeri", "Ntwali", "Nyarure"],
      "Ngera": ["Bitare", "Mukuge", "Murama", "Nyamirama", "Nyanza", "Yaramba"],
      "Ngoma": ["Fugi", "Kibangu", "Kiyonza", "Mbuye", "Nyamirama", "Rubona"],
      "Nyabimata": ["Gihemvu", "Kabere", "Mishungero", "Nyabimata", "Ruhinga"],
      "Nyagisozi": ["Maraba", "Mwoya", "Nkakwa", "Nyagisozi"],
      "Ruheru": ["Gitita", "Kabere", "Remera", "Ruyenzi", "Uwumusebeya"],
      "Ruramba": ["Gabiro", "Giseke", "Nyarugano", "Rugogwe", "Ruramba"],
      "Rusenge": ["Bunge", "Cyuna", "Gikunzi", "Mariba", "Raranzige", "Rusenge"]
    },
    "Ruhango": {
      "Bweramana": ["Buhanda", "Gitisi", "Murama", "Rubona", "Rwinyana"],
      "Byimana": ["Kamusenyi", "Kirengeri", "Mahembe", "Mpanda", "Muhororo", "Ntenyo", "Nyakabuye"],
      "Kabagali": ["Bihembe", "Karambi", "Munanira", "Remera", "Rwesero", "Rwoga"],
      "Kinazi": ["Burima", "Gisali", "Kinazi", "Rubona", "Rutabo"],
      "Kinihira": ["Bweramvura", "Gitinda", "Kirwa", "Muyunzwe", "Nyakogo", "Rukina"],
      "Mbuye": ["Cyanza", "Gisanga", "Kabuga", "Kizibere", "Mbuye", "Mwendo", "Nyakarekare"],
      "Mwendo": ["Gafunzo", "Gishweru", "Kamujisho", "Kigarama", "Kubutare", "Mutara", "Nyabibugu", "Saruheshyi"],
      "Ntongwe": ["Gako", "Kareba", "Kayenzi", "Kebero", "Nyagisozi", "Nyakabungo", "Nyarurama"],
      "Ruhango": ["Buhoro", "Bunyogombe", "Gikoma", "Munini", "Musamo", "Nyamagana", "Rwoga", "Tambwe"]
    }
  },
  "West": {
    "Karongi": {
      "Bwishyura": ["Burunga", "Gasura", "Gitarama", "Kayenzi", "Kibuye", "Kiniha", "Nyarusazi"],
      "Gashari": ["Birambo", "Musasa", "Mwendo", "Rugobagoba", "Tongati"],
      "Gishyita": ["Buhoro", "Cyanya", "Kigarama", "Munanira", "Musasa", "Ngoma"],
      "Gitesi": ["Gasharu", "Gitega", "Kanunga", "Kirambo", "Munanira", "Nyamiringa", "Ruhinga", "Rwariro"],
      "Mubuga": ["Kagabiro", "Murangara", "Nyagatovu", "Ryaruhanga"],
      "Murambi": ["Mubuga", "Muhororo", "Nkoto", "Nyarunyinya", "Shyembe"],
      "Murundi": ["Bukiro", "Kabaya", "Kamina", "Kareba", "Nyamushishi", "Nzaratsi"],
      "Mutuntu": ["Byogo", "Gasharu", "Gisayura", "Kanyege", "Kinyonzwe", "Murengezo", "Rwufi"],
      "Rubengera": ["Bubazi", "Gacaca", "Gisanze", "Gitwa", "Kibirizi", "Mataba", "Nyarugenge", "Ruragwe"],
      "Rugabano": ["Gisiza", "Gitega", "Gitovu", "Kabuga", "Mubuga", "Mucyimba", "Rufungo", "Rwungo", "Tyazo"],
      "Ruganda": ["Biguhu", "Kabingo", "Kinyovu", "Kivumu", "Nyabikeri", "Nyamugwagwa", "Rubona", "Rugobagoba"],
      "Rwankuba": ["Bigugu", "Bisesero", "Gasata", "Munini", "Nyakamira", "Nyarusanga", "Rubazo", "Rubumba"],
      "Twumba": ["Bihumbe", "Gakuta", "Gisovu", "Gitabura", "Kavumu", "Murehe", "Rutabi"]
    },
    "Ngororero": {
      "Bwira": ["Bungwe", "Cyahafi", "Gashubi", "Kabarondo", "Ruhindage"],
      "Gatumba": ["Cyome", "Gatsibo", "Kamasiga", "Karambo", "Ruhanga", "Rusumo"],
      "Hindiro": ["Gatare", "Gatega", "Kajinge", "Marantima", "Rugendabari", "Runyinya"],
      "Kabaya": ["Busunzu", "Gaseke", "Kabaya", "Mwendo", "Ngoma", "Nyenyeri"],
      "Kageyo": ["Kageshi", "Kirwa", "Mukore", "Muramba", "Nyamata", "Rwamamara"],
      "Kavumu": ["Birembo", "Gitwa", "Murinzi", "Nyamugeyo", "Rugeshi", "Tetero"],
      "Matyazo": ["Binana", "Gitega", "Matare", "Rutare", "Rwamiko"],
      "Muhanda": ["Bugarura", "Gasiza", "Mashya", "Nganzo", "Ngoma", "Rutagara"],
      "Muhororo": ["Bweramana", "Mubuga", "Myiha", "Rugogwe", "Rusororo", "Sanza"],
      "Ndaro": ["Bijyojyo", "Bitabage", "Kabageshi", "Kibanda", "Kinyovi"],
      "Ngororero": ["Kaseke", "Kazabe", "Mugano", "Nyange", "Rususa", "Torero"],
      "Nyange": ["Bambiro", "Gaseke", "Nsibo", "Vuganyana"],
      "Sovu": ["Birembo", "Kagano", "Kanyana", "Musenyi", "Nyabipfura", "Rutovu"]
    },
    "Nyabihu": {
      "Bigogwe": ["Arusha", "Basumba", "Kijote", "Kora", "Muhe", "Rega"],
      "Jenda": ["Bukinanyana", "Gasizi", "Kabatezi", "Kareba", "Nyirakigugu", "Rega"],
      "Jomba": ["Gasiza", "Gasura", "Gisizi", "Guriro", "Kavumu", "Nyamitanzi"],
      "Kabatwa": ["Batikoti", "Cyamvumba", "Gihorwe", "Myuga", "Ngando", "Rugarama"],
      "Karago": ["Busoro", "Cyamabuye", "Gatagara", "Gihirwa", "Kadahenda", "Karengera"],
      "Kintobo": ["Gatovu", "Kintobo", "Nyagisozi", "Nyamugari", "Rukondo", "Ryinyo"],
      "Mukamira": ["Gasizi", "Jaba", "Kanyove", "Rubaya", "Rugeshi", "Rukoma", "Rurengeri"],
      "Muringa": ["Gisizi", "Mulinga", "Mwiyanike", "Nkomane", "Nyamasheke", "Rwantobo"],
      "Rambura": ["Birembo", "Guriro", "Kibisabo", "Mutaho", "Nyundo", "Rugamba"],
      "Rugera": ["Gakoro", "Marangara", "Nyagahondo", "Nyarutembe", "Rurembo", "Tyazo"],
      "Rurembo": ["Gahondo", "Gitega", "Kirimbogo", "Murambi", "Mwana", "Rwaza"],
      "Shyira": ["Cyimanzovu", "Kanyamitana", "Kintarure", "Mpinga", "Mutanda", "Shaki"]
    },
    "Nyamasheke": {
      "Bushekeri": ["Buvungira", "Mpumbu", "Ngoma", "Nyarusange"],
      "Bushenge": ["Gasheke", "Impala", "Kagatamu", "Karusimbi"],
      "Cyato": ["Bisumo", "Murambi", "Mutongo", "Rugari"],
      "Gihombo": ["Butare", "Gitwa", "Jarama", "Kibingo", "Mubuga"],
      "Kagano": ["Gako", "Mubumbano", "Ninzi", "Rwesero", "Shara"],
      "Kanjongo": ["Kibogora", "Kigarama", "Kigoya", "Raro", "Susa"],
      "Karambi": ["Gasovu", "Gitwe", "Kabuga", "Kagarama", "Rushyarara"],
      "Karengera": ["Gasayo", "Gashashi", "Higiro", "Miko", "Mwezi"],
      "Kirimbi": ["Cyimpindu", "Karengera", "Muhororo", "Nyarusange"],
      "Macuba": ["Gatare", "Mutongo", "Nyakabingo", "Rugari", "Vugangoma"],
      "Mahembe": ["Gisoke", "Kagarama", "Nyagatare", "Nyakavumu"],
      "Nyabitekeri": ["Kigabiro", "Kinunga", "Mariba", "Muyange", "Ntango"],
      "Rangiro": ["Banda", "Gakenke", "Jurwe", "Murambi"],
      "Ruharambuga": ["Kanazi", "Ntendezi", "Save", "Wimana"],
      "Shangi": ["Burimba", "Mataba", "Mugera", "Nyamugari", "Shangi"]
    },
    "Rubavu": {
      "Bugeshi": ["Buringo", "Butaka", "Hehu", "Kabumba", "Mutovu", "Nsherima", "Rusiza"],
      "Busasamana": ["Gacurabwenge", "Gasiza", "Gihonga", "Kageshi", "Makoro", "Nyacyonga", "Rusura"],
      "Cyanzarwe": ["Busigari", "Cyanzarwe", "Gora", "Kinyanzovu", "Makurizo", "Rwangara", "Rwanzekuma", "Ryabizige"],
      "Gisenyi": ["Amahoro", "Bugoyi", "Kivumu", "Mbugangari", "Nengo", "Rubavu", "Umuganda"],
      "Kanama": ["Kamuhoza", "Karambo", "Mahoko", "Musabike", "Nkomane", "Rusongati", "Yungwe"],
      "Kanzenze": ["Kanyirabigogo", "Kirerema", "Muramba", "Nyamikongi", "Nyamirango", "Nyaruteme"],
      "Mudende": ["Bihungwe", "Kanyundo", "Micinyiro", "Mirindi", "Ndoranyi", "Rungu", "Rwanyakayaga"],
      "Nyakiriba": ["Bisizi", "Gikombe", "Kanyefurwe", "Nyarushyamba"],
      "Nyamyumba": ["Burushya", "Busoro", "Kinigi", "Kiraga", "Munanira", "Rubona"],
      "Nyundo": ["Bahimba", "Gatovu", "Kavomo", "Kigarama", "Mukondo", "Nyundo", "Terimbere"],
      "Rubavu": ["Buhaza", "Burinda", "Byahi", "Gikombe", "Murambi", "Murara", "Rukoko"],
      "Rugerero": ["Basa", "Gisa", "Kabilizi", "Muhira", "Rugerero", "Rushubi", "Rwaza"]
    },
    "Rusizi": {
      "Bugarama": ["Nyange", "Pera", "Ryankana"],
      "Butare": ["Butanda", "Gatereri", "Nyamihanda", "Rwambogo"],
      "Bweyeye": ["Gikungu", "Kiyabo", "Murwa", "Nyamuzi", "Rasano"],
      "Gashonga": ["Birembo", "Buhokoro", "Kabakobwa", "Kacyuma", "Kamurehe", "Karemereye", "Muti", "Rusayo"],
      "Giheke": ["Cyendajuru", "Gakomeye", "Giheke", "Kamashangi", "Kigenge", "Ntura", "Rwega", "Turambi"],
      "Gihundwe": ["Burunga", "Gatsiro", "Gihaya", "Kagara", "Kamatita", "Shagasha"],
      "Gikundamvura": ["Kizura", "Mpinga", "Nyamigina"],
      "Gitambi": ["Cyingwa", "Gahungeri", "Hangabashi", "Mashesha"],
      "Kamembe": ["Cyangugu", "Gihundwe", "Kamashangi", "Kamurera", "Ruganda"],
      "Muganza": ["Cyarukara", "Gakoni", "Shara"],
      "Mururu": ["Gahinga", "Kabahinda", "Kabasigirira", "Kagarama", "Karambi", "Miko", "Tara"],
      "Nkanka": ["Gitwa", "Kamanyenga", "Kangazi", "Kinyaga", "Rugabano"],
      "Nkombo": ["Bigoga", "Bugarura", "Ishywa", "Kamagimbo", "Rwenje"],
      "Nkungu": ["Gatare", "Kiziguro", "Mataba", "Ryamuhirwa"],
      "Nyakabuye": ["Gasebeya", "Gaseke", "Kamanu", "Kiziho", "Mashyuza", "Nyabintare"],
      "Nyakarenzo": ["Gatare", "Kabagina", "Kabuye", "Kanoga", "Karangiro", "Murambi", "Rusambu"],
      "Nzahaha": ["Butambamo", "Kigenge", "Murya", "Nyenji", "Rebero", "Rwinzuki"],
      "Rwimbogo": ["Karenge", "Muhehwe", "Mushaka", "Rubugu", "Ruganda"]
    },
    "Rutsiro": {
      "Boneza": ["Bushaka", "Kabihogo", "Nkira", "Remera"],
      "Gihango": ["Bugina", "CongoNil", "Mataba", "Murambi", "Ruhingo", "Shyembe", "Teba"],
      "Kigeyo": ["Buhindure", "Nkora", "Nyagahinika", "Rukaragata"],
      "Kivumu": ["Bunyoni", "Bunyunju", "Kabere", "Kabujenje", "Karambi", "Nganzo"],
      "Manihira": ["Haniro", "Muyira", "Tangabo"],
      "Mukura": ["Kabuga", "Kagano", "Kageyo", "Kagusa", "Karambo", "Mwendo"],
      "Murunda": ["Kirwa", "Mburamazi", "Rugeyo", "Twabugezi"],
      "Musasa": ["Gabiro", "Gisiza", "Murambi", "Nyarubuye"],
      "Mushonyi": ["Biruyi", "Kaguriro", "Magaba", "Rurara"],
      "Mushubati": ["Bumba", "Cyarusera", "Gitwa", "Mageragere", "Sure"],
      "Nyabirasi": ["Busuku", "Cyivugiza", "Mubuga", "Ngoma", "Terimbere"],
      "Ruhango": ["Gatare", "Gihira", "Kavumu", "Nyakarera", "Rugasa", "Rundoyi"],
      "Rusebeya": ["Kabona", "Mberi", "Remera", "Ruronde"]
    }
  }
};

/* Lookups. Province names are keys in GEO; districts are unique nationally. */
const PROVINCE_OF = {}, SECTOR_DISTRICTS = {};
Object.entries(GEO).forEach(([p, ds]) => Object.entries(ds).forEach(([d, ss]) => {
  PROVINCE_OF[d] = p;
  Object.keys(ss).forEach(s => (SECTOR_DISTRICTS[s] = SECTOR_DISTRICTS[s] || []).push(d));
}));
const PROV_LABEL = {
  en: { East: 'Eastern Province', Kigali: 'Kigali City', North: 'Northern Province', South: 'Southern Province', West: 'Western Province' },
  rw: { East: 'Iburasirazuba', Kigali: 'Umujyi wa Kigali', North: 'Amajyaruguru', South: 'Amajyepfo', West: 'Iburengerazuba' }
};
const provinces = () => Object.keys(GEO).sort();
const districtsOf = p => (p ? Object.keys(GEO[p] || {}) : Object.keys(PROVINCE_OF)).sort((a, b) => a.localeCompare(b));
const sectorsOf = d => Object.keys((GEO[PROVINCE_OF[d]] || {})[d] || {});
const cellsOf = (d, s) => (((GEO[PROVINCE_OF[d]] || {})[d] || {})[s]) || [];
const GEO_TOTALS = (() => {
  let d = 0, s = 0, c = 0;
  Object.values(GEO).forEach(ds => Object.values(ds).forEach(ss => { d++; s += Object.keys(ss).length; Object.values(ss).forEach(cs => { c += cs.length; }); }));
  return { districts: d, sectors: s, cells: c };
})();


/* ===== core.js: Helpers, translations, encryption, storage layer, seed data ===== */
/* Registration National - core: helpers, i18n, AES-256-GCM encryption, simulated server (PostgreSQL stand-in) */
const G = id => document.getElementById(id);
const LS = localStorage;
const J = (k, d) => { try {
  const v = JSON.parse(LS.getItem(k));
  return v ?? d;
} catch { return d; } };
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const uid = () => crypto.randomUUID();
const rnd = n => Array.from({ length: n }, () => Math.floor(Math.random() * 10)).join('');
const nidOK = v => /^\d{16}$/.test(v || '');
const phOK = v => /^07[2389]\d{7}$/.test(v || '');
/* Storage: use the Python server (shared SQLite database) when it is available, otherwise this browser's localStorage */
function xhr(method, url, body) {
  const x = new XMLHttpRequest();
  x.open(method, url, false);
  if (body) x.setRequestHeader('Content-Type', 'application/json');
  x.send(body || null);
  return x;
}
const apiOK = (() => {
  try { return xhr('GET', '/api/ping').status === 200; } catch { return false; }
})();
const S = (k, v) => {
  if (k === 'rn_server' && apiOK) xhr('POST', '/api/db', JSON.stringify(v));
  else LS.setItem(k, JSON.stringify(v));
};
const DB = () => {
  if (!apiOK) return J('rn_server', null);
  const x = xhr('GET', '/api/db');
  return x.status === 200 ? JSON.parse(x.responseText) : null;
};
const net = () => LS.getItem('rn_net') !== 'off';

/* Jurisdictions: the full national hierarchy (province, district, sector, cell) lives in js/geo.js */

/* i18n: Kinyarwanda + English (NFR 4 / 6.5) */
const L = {
  en: { app: 'Registration National', welcome: 'Welcome', hero1: 'Every birth counted, even offline.', hero2: 'Register newborns at home, sync later, and send parents a tracking code by SMS.', register: 'Register a newborn', cancel: 'Cancel', login: 'Sign in', user: 'Phone number or username', pin: 'PIN', logout: 'Log out', online: 'Online', offline: 'Offline', records: 'My records', newrec: 'New birth record', step: 'Step', child: 'Child', mother: 'Mother', father: 'Father (optional)', witness1: 'Witness 1', witness2: 'Witness 2 (optional)', given: 'Given name', family: 'Family name', dob: 'Date of birth', pob: 'Place of birth', gender: 'Gender', M: 'Male', F: 'Female', nid: 'National ID (16 digits)', phone: 'Phone (07XXXXXXXX)', address: 'Address', next: 'Next', back: 'Back', savedraft: 'Save draft', submit: 'Submit', review: 'Review and submit', photo: 'Photo of parent ID (optional)', none: 'No records yet', tracking: 'Tracking code', edit: 'Edit', del: 'Delete', syncnow: 'Sync now', waiting: 'Waiting to sync', req: 'Required', nid16: 'ID must be 16 digits', phbad: 'Use format 07XXXXXXXX', dobfut: 'Date cannot be in the future', fix: 'Fix the highlighted fields', saved: 'Saved offline. It will sync when you are online.', sent: 'Submitted and synced', draftsaved: 'Draft saved', offnote: 'You are offline. Records stay queued.', synced: 'Synced records:', Draft: 'Draft', Queued: 'Queued', Synced: 'Synced', Approved: 'Approved', Flagged: 'Needs correction' },
  rw: { welcome: 'Murakaza neza', hero1: 'Buri mwana wese yandikwe, nubwo nta interineti.', hero2: 'Andika abana bavutse mu ngo, wohereze nyuma, ababyeyi bahabwe kode ikurikirana kuri SMS.', register: 'Andika umwana mushya', cancel: 'Reka', login: 'Injira', user: 'Telefone cyangwa izina', pin: "Umubare w'ibanga", logout: 'Sohoka', online: 'Hari interineti', offline: 'Nta interineti', records: 'Inyandiko zanjye', newrec: 'Andika umwana mushya', step: 'Intambwe', child: 'Umwana', mother: 'Mama', father: 'Papa (si ngombwa)', witness1: 'Umutangabuhamya 1', witness2: 'Umutangabuhamya 2 (si ngombwa)', given: 'Izina bwite', family: "Izina ry'umuryango", dob: "Itariki y'amavuko", pob: 'Aho yavukiye', gender: 'Igitsina', M: 'Gabo', F: 'Gore', nid: 'Indangamuntu (imibare 16)', phone: 'Telefone', address: 'Aho atuye', next: 'Komeza', back: 'Subira inyuma', savedraft: "Bika nk'inyandiko", submit: 'Ohereza', review: 'Kureba no kohereza', none: 'Nta nyandiko zihari', tracking: 'Kode ikurikirana', edit: 'Hindura', del: 'Siba', syncnow: 'Ohereza ubu', waiting: 'Zitegereje kohereza', req: 'Bikenewe', nid16: 'Indangamuntu igomba kuba imibare 16', Draft: 'Inyandiko', Queued: 'Mu murongo', Synced: 'Byoherejwe', Approved: 'Byemejwe', Flagged: 'Bikosorwe' }
};
/* Additional UI text (portal, dashboards, messages) */
Object.assign(L.en, {
  "dashboard": "Dashboard",
  "reviewrec": "Review records",
  "coverage": "Coverage",
  "users": "Users",
  "smslog": "SMS log",
  "allopt": "All",
  "cell": "Cell",
  "status": "Status",
  "subfrom": "Submitted from",
  "cellvillage": "Cell / Village",
  "submitted": "Submitted",
  "open": "Open",
  "nomatch": "No records match.",
  "sector": "Sector",
  "village": "Village",
  "birthrec": "Birth record",
  "commentreq": "Comment (required to return the record)",
  "approve": "Approve",
  "returnchw": "Return to CHW",
  "close": "Close",
  "needcomment": "Add a comment so the CHW knows what to fix",
  "approvedsms": "Approved. SMS sent to parent.",
  "returned": "Returned to CHW",
  "covtitle": "Coverage by cell: {a} approved of {t} submitted",
  "pending": "Pending",
  "retshort": "Returned",
  "apprate": "Approved rate",
  "recsub": "Records submitted",
  "awaiting": "Awaiting review",
  "returnedchw": "Returned to CHW",
  "approvalrate": "Approval rate",
  "accounts": "Accounts",
  "smssent": "SMS sent",
  "startTitle": "Getting started",
  "start1": "Open <b>Users</b> and create a Sector registrar and a CHW (choose their sector, cell and village).",
  "start2": "Sign in as the CHW and register a newborn.",
  "start3": "Sign in as the registrar to review and approve it.",
  "last7": "Submissions, last 7 days",
  "recstatus": "Record status",
  "busiest": "Busiest cells",
  "norecyet": "No records yet.",
  "recent": "Recent records",
  "nothingsub": "Nothing submitted yet.",
  "time": "Time",
  "to": "To",
  "message": "Message",
  "nosms": "No SMS sent yet. Approve a record in the registrar portal.",
  "name": "Name",
  "role": "Role",
  "loginlbl": "Login",
  "save": "Save",
  "remove": "Remove",
  "createacct": "Create account",
  "fullname": "Full name",
  "phoneuser": "Phone / username",
  "pin4": "4-digit PIN",
  "cellchw": "Cell (CHW)",
  "villagechw": "Village (CHW)",
  "role_chw": "CHW",
  "role_registrar": "Sector registrar",
  "role_admin": "Administrator",
  "userbad": "Enter a name, login and a 4-digit PIN",
  "dup": "That login already exists",
  "created": "Account created",
  "savedok": "Saved",
  "smstext": "Registration National: birth record for {name} approved. Tracking code {code}.",
  "offbanner": "You are offline. Records are saved on this phone and sync automatically when you reconnect.",
  "oldq": "Queued for {n} days. Connect soon (30-day limit).",
  "hint_pob": "Village or health facility",
  "hint_phone": "We send the tracking code to this number by SMS",
  "thisweek": "This week",
  "accnote": "Accounts are created by your administrator.",
  "wrongcred": "Wrong phone/username or PIN.",
  "wrongoff": " Offline sign-in only works for accounts used on this device.",
  "offtext": "The registrar and admin portals need a connection. Switch the network toggle back to Online.",
  "nettip": "Tap to simulate losing or regaining the network"
});
Object.assign(L.rw, {
  "dashboard": "Imbonerahamwe",
  "reviewrec": "Gusuzuma inyandiko",
  "coverage": "Ingano y'iyandikishwa",
  "users": "Abakoresha",
  "smslog": "Ubutumwa bwa SMS",
  "allopt": "Byose",
  "cell": "Akagari",
  "status": "Imiterere",
  "subfrom": "Zoherejwe guhera",
  "cellvillage": "Akagari / Umudugudu",
  "submitted": "Yoherejwe",
  "open": "Fungura",
  "nomatch": "Nta nyandiko zihuye.",
  "sector": "Umurenge",
  "village": "Umudugudu",
  "birthrec": "Inyandiko y'ivuka",
  "commentreq": "Ibisobanuro (bikenewe mu gusubiza inyandiko)",
  "approve": "Emeza",
  "returnchw": "Subiza umujyanama",
  "close": "Funga",
  "needcomment": "Andika ibisobanuro kugira ngo umujyanama amenye icyo akosora",
  "approvedsms": "Byemejwe. SMS yoherejwe ku mubyeyi.",
  "returned": "Yasubijwe umujyanama",
  "covtitle": "Ingano ku kagari: {a} byemejwe muri {t} byoherejwe",
  "pending": "Zitegereje",
  "retshort": "Zasubijwe",
  "apprate": "Igipimo cy'ibyemejwe",
  "recsub": "Inyandiko zoherejwe",
  "awaiting": "Zitegereje gusuzumwa",
  "returnedchw": "Zasubijwe umujyanama",
  "approvalrate": "Igipimo cy'ibyemejwe",
  "accounts": "Konti",
  "smssent": "SMS zoherejwe",
  "startTitle": "Tangirira hano",
  "start1": "Fungura <b>Abakoresha</b> maze ukore konti y'umwanditsi w'irangamimerere n'iy'umujyanama w'ubuzima (uhitemo umurenge, akagari n'umudugudu).",
  "start2": "Injira nk'umujyanama w'ubuzima maze wandike umwana wavutse.",
  "start3": "Injira nk'umwanditsi w'irangamimerere kugira ngo usuzume kandi wemeze inyandiko.",
  "last7": "Inyandiko zoherejwe mu minsi 7 ishize",
  "recstatus": "Uko inyandiko zihagaze",
  "busiest": "Utugari dufite inyandiko nyinshi",
  "norecyet": "Nta nyandiko zihari.",
  "recent": "Inyandiko za vuba",
  "nothingsub": "Nta nyandiko ziroherezwa.",
  "time": "Igihe",
  "to": "Kuri",
  "message": "Ubutumwa",
  "nosms": "Nta SMS iroherezwa. Emeza inyandiko ku rubuga rw'umwanditsi.",
  "name": "Izina",
  "role": "Uruhare",
  "loginlbl": "Telefone / izina",
  "save": "Bika",
  "remove": "Kuraho",
  "createacct": "Kora konti",
  "fullname": "Amazina yombi",
  "phoneuser": "Telefone / izina",
  "pin4": "Umubare w'ibanga (imibare 4)",
  "cellchw": "Akagari (umujyanama)",
  "villagechw": "Umudugudu (umujyanama)",
  "role_chw": "Umujyanama w'ubuzima",
  "role_registrar": "Umwanditsi w'irangamimerere",
  "role_admin": "Umuyobozi wa sisitemu",
  "userbad": "Andika izina, telefone cyangwa izina ry'ukoresha, n'umubare w'ibanga w'imibare 4",
  "dup": "Iyo konti isanzwe ihari",
  "created": "Konti yakozwe",
  "savedok": "Byabitswe",
  "smstext": "Registration National: inyandiko y'ivuka ya {name} yemejwe. Kode ikurikirana: {code}.",
  "offbanner": "Nta interineti. Inyandiko zibikwa kuri telefone kandi zoherezwa ubwazo interineti nigaruka.",
  "oldq": "Mu murongo hashize iminsi {n}. Shaka interineti vuba (imipaka ni iminsi 30).",
  "hint_pob": "Umudugudu cyangwa ikigo nderabuzima",
  "hint_phone": "Kode ikurikirana izoherezwa kuri iyi telefone kuri SMS",
  "thisweek": "Iki cyumweru",
  "accnote": "Konti zikorwa n'umuyobozi wa sisitemu.",
  "wrongcred": "Telefone cyangwa izina cyangwa umubare w'ibanga si byo.",
  "wrongoff": " Nta interineti: winjira gusa ukoresheje konti zigeze gukoreshwa kuri iki gikoresho.",
  "offtext": "Urubuga rw'umwanditsi n'urw'umuyobozi bikenera interineti. Subiza interineti kuri \"Hari interineti\".",
  "nettip": "Kanda kugira ngo wigane gutakaza cyangwa kongera kubona interineti"
});
Object.assign(L.rw, {
  "app": "Registration National",
  "photo": "Ifoto y'indangamuntu y'umubyeyi (si ngombwa)",
  "phbad": "Koresha imiterere 07XXXXXXXX",
  "dobfut": "Itariki ntishobora kuba mu gihe kizaza",
  "fix": "Kosora ibyagaragajwe",
  "saved": "Byabitswe nta interineti. Bizoherezwa interineti nigaruka.",
  "sent": "Byoherejwe",
  "draftsaved": "Inyandiko yabitswe",
  "offnote": "Nta interineti. Inyandiko ziguma mu murongo.",
  "synced": "Byoherejwe:"
});
Object.assign(L.en, {
  "province": "Province",
  "district": "District",
  "sectors": "Sectors",
  "cells": "Cells",
  "pickdistrict": "Select district",
  "picksector": "Select sector",
  "pickcell": "Select cell",
  "needgeo": "Choose a district and sector (and a cell for a CHW)",
  "covnational": "National coverage: {a} approved of {t} submitted",
  "covscope": "Showing {c} cells",
  "covdrill": "Select a district to see its sectors and cells.",
  "covall": "All districts",
  "covback": "Back to all districts",
  "geoinfo": "{d} districts, {s} sectors, {c} cells"
});
Object.assign(L.rw, {
  "province": "Intara",
  "district": "Akarere",
  "sectors": "Imirenge",
  "cells": "Utugari",
  "pickdistrict": "Hitamo akarere",
  "picksector": "Hitamo umurenge",
  "pickcell": "Hitamo akagari",
  "needgeo": "Hitamo akarere n'umurenge (n'akagari ku mujyanama w'ubuzima)",
  "covnational": "Ingano mu gihugu: {a} byemejwe muri {t} byoherejwe",
  "covscope": "Hagaragajwe utugari {c}",
  "covdrill": "Hitamo akarere urebe imirenge n'utugari twaryo.",
  "covall": "Uturere twose",
  "covback": "Subira ku turere twose",
  "geoinfo": "Uturere {d}, imirenge {s}, utugari {c}"
});
L.en.offtitle = 'Offline';
L.rw.offtitle = 'Nta interineti';
const WEEKDAYS_RW = ['Cyu', 'Mbe', 'Kab', 'Gat', 'Kan', 'Gnu', 'Gnd'];

let lang = LS.getItem('rn_lang') || 'en';
const t = k => (L[lang] && L[lang][k]) || L.en[k] || k;

/* AES-256-GCM via Web Crypto; key derived from PIN with PBKDF2 (stand-in for SQLCipher on the phone) */
const enc = new TextEncoder(), dec = new TextDecoder();
const b64 = b => { let s = '';
for (const x of new Uint8Array(b)) s += String.fromCharCode(x);
return btoa(s); };
const unb64 = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));
const sha = async s => b64(await crypto.subtle.digest('SHA-256', enc.encode(s)));
async function deriveKey(pin, salt) {
  const m = await crypto.subtle.importKey('raw', enc.encode(pin), 'PBKDF2', false, ['deriveKey']);
  return crypto.subtle.deriveKey({ name: 'PBKDF2', salt: enc.encode(salt), iterations: 100000, hash: 'SHA-256' }, m, { name: 'AES-GCM', length: 256 }, false, ['encrypt', 'decrypt']);
}
async function seal(key, obj) {
  const iv = crypto.getRandomValues(new Uint8Array(12));
  return b64(iv) + '.' + b64(await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, key, enc.encode(JSON.stringify(obj))));
}
async function unseal(key, s) {
  if (!s) return [];
  const [iv, ct] = s.split('.');
  return JSON.parse(dec.decode(await crypto.subtle.decrypt({ name: 'AES-GCM', iv: unb64(iv) }, key, unb64(ct))));
}

const logS = (db, m) => { db.log.unshift({ at: new Date().toISOString(), m });
db.log.length = Math.min(db.log.length, 100); };

/* Seed demo data on first load */
/* First run: create one bootstrap administrator (admin / 1234). The admin then creates every other account (FR 1.2). */
/* Older data stored only a sector name. Add the district when that sector name belongs to exactly one district. */
function migrateGeo(db) {
  let changed = false;
  const fix = x => {
    const ds = x && x.sector && !x.district && SECTOR_DISTRICTS[x.sector];
    if (ds && ds.length === 1) {
      x.district = ds[0];
      changed = true;
    }
  };
  db.users.forEach(fix);
  db.records.forEach(fix);
  return changed;
}
async function seed() {
  const existing = DB();
  if (existing) {
    if (migrateGeo(existing)) S('rn_server', existing);
    return;
  }
  const db = {
    users: [{ id: 'u-admin', name: 'Administrator', role: 'admin', login: 'admin', hash: await sha('admin:1234'), district: '', sector: '', cell: '', village: '' }],
    records: [], sms: [], log: []
  };
  logS(db, 'System initialised');
  S('rn_server', db);
}

/* Refresh the offline credential cache whenever the device is online (FR 1.1) */
function refreshCache() {
  const db = DB();
  if (net() && db) S('rn_cred', db.users);
}

const tiles = l => `<div class="tiles">${l.map(x => `<div class="tile ${x[2] || ''}"><b>${x[0]}</b>
  <span>${x[1]}</span></div>`).join('')}</div>`;

/* Submissions per day for the last 7 days (shared by the CHW and portal dashboards) */
const weekChart = rs => {
  const days = Array.from({ length: 7 }, (_, i) => new Date(Date.now() - (6 - i) * 864e5).toISOString().slice(0, 10));
  const per = days.map(d => rs.filter(r => (r.createdAt || '').slice(0, 10) === d).length);
  const max = Math.max(1, ...per);
  return `<div class="bars">${days.map((d, i) => `<div class="bcol"><b>${per[i]}</b><div class="bw"><i style="height:${per[i] / max * 100}%"></i></div><small>${(lang === 'rw' ? WEEKDAYS_RW[new Date(d + 'T12:00:00').getDay()] : new Date(d + 'T12:00:00').toLocaleDateString(undefined, { weekday: 'short' }))}</small></div>`).join('')}</div>`;
};


/* ===== chw.js: CHW mobile client ===== */
/* CHW mobile client: offline intake wizard, encrypted local DB, auto-sync (FR 1-3) */
const STEPS = [
  { k: 'child', f: ['given', 'family', 'dob', 'pob', 'gender'], r: 1 },
  { k: 'mother', f: ['given', 'family', 'nid', 'phone'], r: 1 },
  { k: 'father', f: ['given', 'family', 'nid', 'phone'], r: 0 },
  { k: 'w1', f: ['given', 'family', 'nid', 'address'], r: 1 },
  { k: 'w2', f: ['given', 'family', 'nid', 'address'], r: 0 }
];
const TITLES = { child: 'child', mother: 'mother', father: 'father', w1: 'witness1', w2: 'witness2' };
let W = null, busy = false;
const lk = () => 'rn_local_' + ME.id;
const loadLocal = () => unseal(KEY, LS.getItem(lk()));
const saveLocal = async a => LS.setItem(lk(), await seal(KEY, a));

/* FR 2.2: validate 16-digit National ID (plus phone/date format) */
function validate(st, d = {}) {
  const e = {}, any = Object.values(d).some(x => x);
  st.f.forEach(f => {
    const v = (d[f] || '').trim();
    const req = st.r ? true : (any && f !== 'phone');
    if (req && !v) e[f] = t('req');
    else if (v) {
      if (f === 'nid' && !nidOK(v)) e[f] = t('nid16');
      if (f === 'phone' && !phOK(v)) e[f] = t('phbad');
      if (f === 'dob' && new Date(v) > new Date()) e[f] = t('dobfut');
    }
  });
  return e;
}
const fmtErr = d => STEPS.some(st => { const x = d[st.k] || {}; return (x.nid && !nidOK(x.nid)) || (x.phone && !phOK(x.phone)); });
function collect() {
  if (W.step >= 5) return;
  const st = STEPS[W.step], o = {};
  st.f.forEach(f => { const el = G('f_' + f); if (el) o[f] = el.value.trim(); });
  W.d[st.k] = o;
}

const hintFor = f => ({ pob: t('hint_pob'), phone: t('hint_phone') })[f];
function setG(g, btn) {
  G('f_gender').value = g;
  btn.parentNode.querySelectorAll('button').forEach(b => b.classList.toggle('on', b === btn));
}
function jump(i) {
  W.step = i;
  W.err = null;
  render();
}
const stepper = () => `<div class="steps">${[0, 1, 2, 3, 4, 5].map(i => `<i class="${i < W.step ? 'done' : i === W.step ? 'cur' : ''}">
  </i>`).join('')}</div>`;
function wizHTML() {
  const s = W.step;
  if (s === 5) return reviewHTML();
  const st = STEPS[s], d = W.d[st.k] || {}, e = W.err || {};
  const inputs = st.f.map(f => {
    let inp, hint = hintFor(f) ? `<div class="hint">${hintFor(f)}</div>` : '';
    if (f === 'gender') inp = `<input type="hidden" id="f_gender" value="${esc(d.gender)}"><div class="seg">${['M', 'F'].map(g => `<button type="button" class="${d.gender === g ? 'on' : ''}" onclick="setG('${g}',this)">${t(g)}</button>`).join('')}</div>`;
    else if (f === 'nid') {
      inp = `<input id="f_nid" value="${esc(d.nid)}" inputmode="numeric" maxlength="16" oninput="this.value=this.value.replace(/\\D/g,'');G('h_nid').textContent=this.value.length+'/16 digits'">`; hint = `<div class="hint" id="h_nid">${(d.nid || '').length}/16 digits</div>`;
    }
    else if (f === 'phone') inp = `<input id="f_phone" value="${esc(d.phone)}" inputmode="tel" maxlength="10" placeholder="07XXXXXXXX" oninput="this.value=this.value.replace(/\\D/g,'')">`;
    else inp = `<input id="f_${f}" value="${esc(d[f])}" ${f === 'dob' ? `type="date" max="${new Date().toISOString().slice(0, 10)}"` : ''}>`;
    return `<label for="f_${f}">${t(f)}</label>${inp}${e[f] ? `<div class="err">${e[f]}</div>` : hint}`;
  }).join('');
  return `<div class="card"><div class="row between" style="margin:0"><span class="muted">${t('step')} ${s + 1}/6</span>
    <button class="text" onclick="goRec()">${t('cancel')}</button></div>${stepper()}<h3>${t(TITLES[st.k])}</h3>${inputs}</div>
  <div class="actions">${s ? `<button class="ghost" onclick="back()">${t('back')}</button>` : ''}<button class="ghost" onclick="draftRec()">${t('savedraft')}</button>
    <button class="go" onclick="next()">${t('next')}</button></div>`;
}
function reviewHTML() {
  const sec = (k, i) => { const en = Object.entries(W.d[k] || {}).filter(x => x[1]);
  return `<div class="sec"><div class="row between" style="margin:0"><h4>${t(TITLES[k])}</h4>
    <button class="text" onclick="jump(${i})">${t('edit')}</button></div>${en.length ? `<dl>${en.map(x => `<dt>${t(x[0])}</dt>
    <dd>${esc(x[0] === 'gender' ? t(x[1]) : x[1])}</dd>`).join('')}</dl>` : '<div class="muted">-</div>'}</div>`; };
  return `<div class="card"><span class="muted">${t('step')} 6/6</span>${stepper()}<h3>${t('review')}</h3>${STEPS.map((x, i) => sec(x.k, i)).join('')}
  <label>${t('photo')}</label><input type="file" accept="image/*" capture="environment" onchange="pick(this)">${W.d.photo ? `<img class="thumb" src="${W.d.photo}" alt="ID photo">` : ''}</div>
  <div class="actions"><button class="ghost" onclick="back()">${t('back')}</button><button class="ghost" onclick="draftRec()">${t('savedraft')}</button>
    <button class="go" onclick="submitRec()">${t('submit')}</button></div>`;
}
function pick(el) {
  const f = el.files[0];
  if (!f) return;
  const img = new Image();
  img.onload = () => { const c = document.createElement('canvas'), k = Math.min(1, 480 / Math.max(img.width, img.height));
  c.width = img.width * k;
  c.height = img.height * k;
  c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
  W.d.photo = c.toDataURL('image/jpeg', .6);
  render(); };
  img.src = URL.createObjectURL(f);
}
function goNew() {
  W = { step: 0, d: {}, id: null, err: null };
  render();
}
function goRec() {
  W = null;
  render();
}
function next() {
  collect();
  const st = STEPS[W.step], e = validate(st, W.d[st.k]);
  if (Object.keys(e).length) {
    W.err = e;
    render();
    return;
  } W.err = null;
  W.step++;
  render();
}
function back() {
  collect();
  W.err = null;
  W.step--;
  render();
}
async function draftRec() {
  collect();
  if (fmtErr(W.d)) return toast(t('fix'));
  await saveRec('Draft');
  toast(t('draftsaved'));
}
async function submitRec() {
  collect();
  for (let i = 0; i < 5; i++) {
    const e = validate(STEPS[i], W.d[STEPS[i].k]);
    if (Object.keys(e).length) {
      W.step = i;
      W.err = e;
      toast(t('fix'));
      return render();
    }
  }
  await saveRec('Queued');
  toast(net() ? t('sent') : t('saved'));
}
async function saveRec(status) {
  const recs = await loadLocal(), d = W.d;
  let r = recs.find(x => x.id === W.id);
  if (!r) {
    r = { id: uid(), createdAt: new Date().toISOString(), chw: ME.id, district: ME.district, sector: ME.sector, cell: ME.cell, village: ME.village };
    recs.push(r);
  }
  Object.assign(r, { child: d.child || {}, mother: d.mother || {}, father: d.father || {}, w1: d.w1 || {}, w2: d.w2 || {}, photo: d.photo || '', status });
  if (status === 'Queued') r.flag = '';
  await saveLocal(recs);
  W = null;
  await render();
  sync();
}
async function editRec(id) {
  const r = (await loadLocal()).find(x => x.id === id);
  W = { step: 0, id, err: null, d: { child: r.child, mother: r.mother, father: r.father, w1: r.w1, w2: r.w2, photo: r.photo } };
  render();
}
async function delRec(id) {
  await saveLocal((await loadLocal()).filter(x => x.id !== id));
  render();
}

/* FR 3.1 / 3.2: auto-sync queued records, pull registrar decisions */
async function sync(manual) {
  if (!ME || ME.role !== 'chw' || busy) return;
  if (!net()) {
    if (manual) toast(t('offnote'));
    return;
  }
  busy = true;
  try {
    const recs = await loadLocal(), db = DB();
    if (!ME) return;
    let n = 0, ch = false;
    for (const r of recs) {
      if (r.status === 'Queued') {
        /* Sector names repeat across districts, so the jurisdiction is District + Sector (older records without a district still match on sector) */
        if (r.sector !== ME.sector || (r.district && r.district !== ME.district)) {
          logS(db, '403 jurisdiction mismatch for ' + ME.login);
          ch = true;
          continue;
        }
        if (!r.district) r.district = ME.district;
        const i = db.records.findIndex(x => x.id === r.id), c = { ...r, status: 'Synced' };
        if (i < 0) db.records.push(c);
        else db.records[i] = c;
        r.status = 'Synced';
        n++;
        ch = true;
      } else if (r.status === 'Synced') {
        const s = db.records.find(x => x.id === r.id);
        if (s && (s.status === 'Approved' || s.status === 'Flagged')) {
          r.status = s.status;
          r.tracking = s.tracking;
          r.flag = s.flag;
          ch = true;
        }
      }
    }
    if (n) logS(db, `POST /sync ${n} record(s) from ${ME.login}: 200 OK`);
    if (ch) {
      S('rn_server', db);
      await saveLocal(recs);
      if (!W) render();
      if (n) toast(t('synced') + ' ' + n);
    }
  } finally {
    busy = false;
  }
}

async function chwHTML() {
  const recs = await loadLocal();
  if (!ME) return '';
  const c = k => recs.filter(r => r.status === k).length, q = c('Queued');
  const banner = net() ? '' : `<div class="banner">${t('offbanner')}</div>`;
  const head = `<div class="phone"><div class="greet"><div><div class="muted">${t('welcome')},</div>
    <h2>${esc(ME.name.split(' ')[0])}</h2></div><span class="chip">${esc(ME.district ? ME.district + ' / ' : '')}${esc(ME.sector)} / ${esc(ME.cell)} / ${esc(ME.village)}</span>
    </div>${banner}`;
  if (W) return head + wizHTML() + '</div>';
  const list = recs.sort((a, b) => b.createdAt.localeCompare(a.createdAt)).map(r => {
    const days = Math.floor((Date.now() - new Date(r.createdAt)) / 864e5);
    return `<div class="rec" data-s="${r.status}"><div class="row between" style="margin:0">
      <b>${esc(r.child.given || '-')} ${esc(r.child.family || '')}</b><span class="badge ${r.status}">${t(r.status)}</span>
      </div>
    <div class="muted">${new Date(r.createdAt).toLocaleDateString()} - ${esc(r.mother.given || '')} ${esc(r.mother.family || '')}</div>
    ${r.tracking ? `<span class="chip big">${t('tracking')}: ${esc(r.tracking)}</span>` : ''}${r.flag ? `<div class="err">${esc(r.flag)}</div>` : ''}${r.status === 'Queued' && days >= 25 ? `<div class="err">${t('oldq').replace('{n}', days)}</div>` : ''}
    ${['Draft', 'Flagged'].includes(r.status) ? `<div class="row"><button class="ghost" onclick="editRec('${r.id}')">${t('edit')}</button>${r.status === 'Draft' ? `<button class="text" onclick="delRec('${r.id}')">${t('del')}</button>` : ''}</div>` : ''}</div>`;
  }).join('');
  return head + `<button class="cta" onclick="goNew()">+ ${t('register')}</button>${tiles([[q, t('Queued'), 'warn'], [c('Synced'), t('Synced')], [c('Approved'), t('Approved'), 'ok'], [c('Flagged'), t('Flagged'), 'bad']])}<div class="card"><h4>${t('thisweek')}</h4>${weekChart(recs)}</div>
  ${q && net() ? `<div class="row between"><span class="muted">${t('waiting')}: ${q}</span><button class="ghost" onclick="sync(true)">${t('syncnow')}</button>
    </div>` : ''}
  ${list || `<div class="empty"><h3>${t('none')}</h3><p>${t('register')}</p></div>`}</div>`;
}


/* ===== portal.js: Registrar portal and admin console ===== */
/* Sector Registrar portal + System Admin console (FR 1.2, FR 4, FR 5). All labels go through t() so they follow the language switch. */
let F = { cell: '', status: '', from: '' }, MODAL = null;
/* Jurisdiction pickers: District > Sector > Cell cascade, because sector names repeat across districts */
const opts = (list, sel, blank) => (blank ? `<option value="">${esc(blank)}</option>` : '') + list.map(x => `<option ${x === sel ? 'selected' : ''}>${esc(x)}</option>`).join('');
const selD = (pre, d) => `<select id="${pre}_d" onchange="geoChg('${pre}','d')">${opts(districtsOf(), d, t('pickdistrict'))}</select>`;
const selS = (pre, d, s) => `<select id="${pre}_s" onchange="geoChg('${pre}','s')">${opts(sectorsOf(d), s, t('picksector'))}</select>`;
const selC = (pre, d, s, c) => `<select id="${pre}_c">${opts(cellsOf(d, s), c, t('pickcell'))}</select>`;
function geoChg(pre, lvl) {
  const d = G(pre + '_d').value;
  if (lvl === 'd') G(pre + '_s').innerHTML = opts(sectorsOf(d), '', t('picksector'));
  const c = G(pre + '_c');
  if (c) c.innerHTML = opts(cellsOf(d, G(pre + '_s').value), '', t('pickcell'));
}
/* A record belongs to a sector when district and sector both match (older records without a district match on sector alone) */
const inSector = (r, d, s) => r.sector === s && (!d || !r.district || r.district === d);
const place = x => [x.district, x.sector, x.cell].filter(Boolean).join(' / ');
const go = tab => {
  TAB = tab;
  MODAL = null;
  render();
};
const tabsHTML = list => `<div class="tabs">${list.map(([k, l]) => `<button class="${TAB === k ? 'on' : ''}" onclick="go('${k}')">${t(l)}</button>`).join('')}</div>`;
const th = keys => keys.map(k => `<th>${t(k)}</th>`).join('');
const day = iso => iso.slice(0, 10);
const person = x => `${esc(x.given)} ${esc(x.family)}`;

function detailHTML(r) {
  const part = (title, x = {}) => {
    const en = Object.entries(x).filter(e => e[1]);
    const rows = en.map(e => `<dt>${t(e[0])}</dt><dd>${esc(e[0] === 'gender' ? t(e[1]) : e[1])}</dd>`).join('');
    return `<div class="sec"><h4>${title}</h4>${en.length ? `<dl>${rows}</dl>` : '<div class="muted">-</div>'}</div>`;
  };
  const act = r.status === 'Synced'
    ? `<label>${t('commentreq')}</label><textarea id="fc" rows="2"></textarea>
       <div class="row"><button onclick="decide('${r.id}',true)">${t('approve')}</button><button class="bad" onclick="decide('${r.id}',false)">${t('returnchw')}</button></div>`
    : (r.flag ? `<div class="err">${esc(r.flag)}</div>` : '') + (r.tracking ? `<p>${t('tracking')}: <b>${esc(r.tracking)}</b></p>` : '');
  return `<div class="modal" onclick="if(event.target===this){MODAL=null;render()}"><div class="card">
    <div class="row between"><h3>${t('birthrec')}</h3><span class="badge ${r.status}">${t(r.status)}</span></div>
    ${part(t('child'), r.child)}${part(t('mother'), r.mother)}${part(t('father'), r.father)}${part(t('witness1'), r.w1)}${part(t('witness2'), r.w2)}
    ${r.photo ? `<img class="thumb" src="${r.photo}" alt="ID">` : ''}${act}
    <button class="ghost" onclick="MODAL=null;render()">${t('close')}</button></div></div>`;
}

/* Dashboard: headline numbers, 7-day submissions, status mix, busiest cells, recent records */
function dashHTML(sc) {
  const db = DB();
  const rs = db.records.filter(r => !sc || inSector(r, sc.d, sc.s));
  const n = k => rs.filter(r => r.status === k).length;
  const total = rs.length, ap = n('Approved'), rate = total ? Math.round(ap / total * 100) : 0;
  const head = [[total, t('recsub')], [n('Synced'), t('awaiting'), 'warn'], [ap, t('Approved'), 'ok'], [n('Flagged'), t('returnedchw'), 'bad'], [rate + '%', t('approvalrate')]];
  if (!sc) head.push([db.users.length, t('accounts')], [db.sms.length, t('smssent')]);
  const mix = [['Synced', t('awaiting')], ['Approved', t('Approved')], ['Flagged', t('retshort')]];
  const cells = {};
  rs.forEach(r => {
    const k = place(r);
    (cells[k] = cells[k] || { t: 0, a: 0 }).t++;
    if (r.status === 'Approved') cells[k].a++;
  });
  const top = Object.entries(cells).sort((a, b) => b[1].t - a[1].t).slice(0, 5);
  const recent = rs.slice().sort((a, b) => b.createdAt.localeCompare(a.createdAt)).slice(0, 5);
  const start = !sc && db.users.length <= 1
    ? `<div class="card start"><h4>${t('startTitle')}</h4><ol><li>${t('start1')}</li><li>${t('start2')}</li><li>${t('start3')}</li></ol></div>` : '';
  const topRows = top.map(c => `<div class="lrow"><span>${esc(c[0])}</span><div class="meter wide"><i style="width:${c[1].a / c[1].t * 100}%"></i></div><b>${c[1].a}/${c[1].t}</b></div>`).join('');
  const recentRows = recent.map(r => `<tr><td>${person(r.child)}</td><td>${esc(place(r))}</td><td>${day(r.createdAt)}</td><td><span class="badge ${r.status}">${t(r.status)}</span></td></tr>`).join('');
  return `${start}${tiles(head)}
  <div class="grid2">
    <div class="card"><h4>${t('last7')}</h4>${weekChart(rs)}</div>
    <div class="card"><h4>${t('recstatus')}</h4>
      <div class="stack">${mix.map(m => `<i class="${m[0]}" style="width:${total ? n(m[0]) / total * 100 : 0}%"></i>`).join('')}</div>
      <div class="legend">${mix.map(m => `<span class="lg"><i class="${m[0]}"></i>${m[1]}: ${n(m[0])}</span>`).join('')}</div>
      <h4 style="margin-top:18px">${t('busiest')}</h4>${topRows || `<p class="muted">${t('norecyet')}</p>`}
    </div>
  </div>
  <div class="card scroll"><h4>${t('recent')}</h4><table>${recentRows || `<tr><td class="muted">${t('nothingsub')}</td></tr>`}</table></div>`;
}

/* FR 4.1 / 4.2: review, approve or return records */
function regHTML() {
  const db = DB();
  let rs = db.records.filter(r => inSector(r, ME.district, ME.sector) && ['Synced', 'Approved', 'Flagged'].includes(r.status));
  if (F.cell) rs = rs.filter(r => r.cell === F.cell);
  if (F.status) rs = rs.filter(r => r.status === F.status);
  if (F.from) rs = rs.filter(r => day(r.createdAt) >= F.from);
  rs.sort((a, b) => b.createdAt.localeCompare(a.createdAt));
  const tabs = tabsHTML([['dash', 'dashboard'], ['rev', 'reviewrec'], ['cov', 'coverage']]);
  let body;
  if (TAB === 'dash') body = dashHTML({ d: ME.district, s: ME.sector });
  else if (TAB === 'cov') body = covHTML({ d: ME.district, s: ME.sector });
  else {
    const cellSel = opts(cellsOf(ME.district, ME.sector), F.cell);
    const statusSel = ['Synced', 'Approved', 'Flagged'].map(s => `<option value="${s}" ${F.status === s ? 'selected' : ''}>${t(s)}</option>`).join('');
    const rows = rs.map(r => `<tr><td>${person(r.child)}</td><td>${person(r.mother)}</td><td>${esc(r.cell)} / ${esc(r.village)}</td><td>${day(r.createdAt)}</td>
      <td><span class="badge ${r.status}">${t(r.status)}</span></td><td><button class="ghost" onclick="MODAL='${r.id}';render()">${t('open')}</button></td></tr>`).join('');
    body = `<div class="card filters">
      <div><label>${t('cell')}</label><select onchange="F.cell=this.value;render()"><option value="">${t('allopt')}</option>${cellSel}</select></div>
      <div><label>${t('status')}</label><select onchange="F.status=this.value;render()"><option value="">${t('allopt')}</option>${statusSel}</select></div>
      <div><label>${t('subfrom')}</label><input type="date" value="${F.from}" onchange="F.from=this.value;render()"></div></div>
      <div class="card scroll"><table><tr>${th(['child', 'mother', 'cellvillage', 'submitted', 'status'])}<th></th></tr>
      ${rows || `<tr><td colspan="6" class="muted">${t('nomatch')}</td></tr>`}</table></div>`;
  }
  const m = MODAL && db.records.find(r => r.id === MODAL);
  return `<div class="greet"><div><div class="muted">${t('role_registrar')}</div><h2>${esc(ME.name)}</h2></div><span class="chip">${ME.district ? esc(ME.district) + ' / ' : ''}${t('sector')} ${esc(ME.sector)}</span></div>${tabs}${body}${m ? detailHTML(m) : ''}`;
}
function decide(id, ok) {
  const db = DB(), r = db.records.find(x => x.id === id);
  if (ok) {
    r.status = 'Approved';
    r.flag = '';
    r.tracking = 'RN-' + new Date().getFullYear() + '-' + rnd(6);
    /* FR 5.1: SMS with the tracking code (written to the SMS log in this prototype) */
    db.sms.unshift({ at: new Date().toISOString(), to: r.mother.phone, text: t('smstext').replace('{name}', `${r.child.given} ${r.child.family}`).replace('{code}', r.tracking) });
    logS(db, `Approved ${r.tracking} by ${ME.login}; SMS queued to ${r.mother.phone}`);
  } else {
    const c = G('fc').value.trim();
    if (!c) return toast(t('needcomment'));
    r.status = 'Flagged';
    r.flag = c;
    logS(db, `Returned record ${r.id.slice(0, 8)} by ${ME.login}`);
  }
  S('rn_server', db);
  MODAL = null;
  render();
  toast(ok ? t('approvedsms') : t('returned'));
}

/* FR 5.2: coverage analytics by cell. A registrar sees the cells of their own sector; the administrator sees all
   30 districts and drills into one district at a time (2,000+ cells would be an unusable single table). */
let CF = { p: '', d: '' };
const tally = rs => ({ tot: rs.length, ap: rs.filter(r => r.status === 'Approved').length, pend: rs.filter(r => r.status === 'Synced').length, fl: rs.filter(r => r.status === 'Flagged').length });
const rateCell = x => {
  const p = x.tot ? Math.round(x.ap / x.tot * 100) : 0;
  return `<div class="meter"><i style="width:${p}%"></i></div>${p}%`;
};
const numCells = x => `<td>${x.tot}</td><td>${x.ap}</td><td>${x.pend}</td><td>${x.fl}</td><td>${rateCell(x)}</td>`;
const sumT = rows => rows.reduce((a, r) => ({ tot: a.tot + r.tot, ap: a.ap + r.ap }), { tot: 0, ap: 0 });
function covHTML(sc) {
  const db = DB();
  if (sc) {
    /* Registrar: every cell of the sector, including cells with no records yet */
    const rows = cellsOf(sc.d, sc.s).map(c => ({ c, ...tally(db.records.filter(r => inSector(r, sc.d, sc.s) && r.cell === c)) }));
    return covTable(rows.map(r => `<tr><td>${esc(sc.s)}</td><td>${esc(r.c)}</td>${numCells(r)}</tr>`), sumT(rows), ['sector', 'cell']);
  }
  /* Administrator */
  const byD = {}, byC = {};
  db.records.forEach(r => {
    (byD[r.district || ''] = byD[r.district || ''] || []).push(r);
    const k = [r.district, r.sector, r.cell].join('|');
    (byC[k] = byC[k] || []).push(r);
  });
  const provSel = `<select onchange="CF.p=this.value;CF.d='';render()"><option value="">${t('allopt')}</option>${provinces().map(p => `<option value="${p}" ${CF.p === p ? 'selected' : ''}>${esc(PROV_LABEL[lang][p])}</option>`).join('')}</select>`;
  const distSel = `<select onchange="CF.d=this.value;render()"><option value="">${t('covall')}</option>${opts(districtsOf(CF.p), CF.d)}</select>`;
  const g = GEO_TOTALS;
  const filters = `<div class="card filters"><div><label>${t('province')}</label>${provSel}</div><div><label>${t('district')}</label>${distSel}</div>
    <div class="muted" style="align-self:end">${t('geoinfo').replace('{d}', g.districts).replace('{s}', g.sectors).replace('{c}', g.cells.toLocaleString())}</div></div>`;
  if (!CF.d) {
    const rows = districtsOf(CF.p).map(d => {
      const secs = sectorsOf(d);
      return { d, ns: secs.length, nc: secs.reduce((n, x) => n + cellsOf(d, x).length, 0), ...tally(byD[d] || []) };
    });
    const tr = rows.map(r => `<tr><td>${esc(PROV_LABEL[lang][PROVINCE_OF[r.d]])}</td><td><b>${esc(r.d)}</b></td><td>${r.ns}</td><td>${r.nc}</td>${numCells(r)}
      <td><button class="ghost" onclick="CF.d='${esc(r.d)}';render()">${t('open')}</button></td></tr>`).join('');
    const T = sumT(rows);
    return `${filters}<div class="card scroll"><b>${t('covnational').replace('{a}', T.ap).replace('{t}', T.tot)}</b>
      <p class="muted">${t('covdrill')}</p><table><tr>${th(['province', 'district', 'sectors', 'cells', 'submitted', 'Approved', 'pending', 'retshort', 'apprate'])}<th></th></tr>${tr}</table></div>`;
  }
  const rows = [];
  sectorsOf(CF.d).forEach(sec => cellsOf(CF.d, sec).forEach(c => rows.push({ sec, c, ...tally(byC[[CF.d, sec, c].join('|')] || []) })));
  const out = covTable(rows.map(r => `<tr><td>${esc(r.sec)}</td><td>${esc(r.c)}</td>${numCells(r)}</tr>`), sumT(rows), ['sector', 'cell']);
  return `${filters}<p><button class="ghost" onclick="CF.d='';render()">&larr; ${t('covback')}</button></p>
    <h3>${esc(CF.d)} <span class="muted">${t('covscope').replace('{c}', rows.length)}</span></h3>${out}`;
}
function covTable(trs, T, lead) {
  return `<div class="card scroll"><b>${t('covtitle').replace('{a}', T.ap).replace('{t}', T.tot)}</b>
    <table><tr>${th([...lead, 'submitted', 'Approved', 'pending', 'retshort', 'apprate'])}</tr>${trs.join('')}</table></div>`;
}

/* FR 1.2: administrator console (accounts, jurisdictions, coverage, SMS log) */
function admHTML() {
  const db = DB();
  const tabs = tabsHTML([['dash', 'dashboard'], ['usr', 'users'], ['cov', 'coverage'], ['sms', 'smslog']]);
  let body;
  if (TAB === 'dash') body = dashHTML(null);
  else if (TAB === 'cov') body = covHTML(null);
  else if (TAB === 'sms') {
    const rows = db.sms.map(s => `<tr><td>${s.at.slice(0, 16).replace('T', ' ')}</td><td>${esc(s.to)}</td><td>${esc(s.text)}</td></tr>`).join('');
    body = `<div class="card scroll"><table><tr>${th(['time', 'to', 'message'])}</tr>${rows || `<tr><td colspan="3" class="muted">${t('nosms')}</td></tr>`}</table></div>`;
  } else {
    const rows = db.users.map(u => {
      const pre = 'u_' + u.id;
      const jur = u.role === 'admin' ? '<td colspan="5"></td>' : `<td>${selD(pre, u.district)}</td><td>${selS(pre, u.district, u.sector)}</td>
        <td>${u.role === 'chw' ? selC(pre, u.district, u.sector, u.cell) : '-'}</td>
        <td>${u.role === 'chw' ? `<input id="uv_${u.id}" value="${esc(u.village)}">` : '-'}</td>
        <td><button class="ghost" onclick="updUser('${u.id}')">${t('save')}</button> ${u.id !== ME.id ? `<button class="ghost" onclick="delUser('${u.id}')">${t('remove')}</button>` : ''}</td>`;
      return `<tr><td>${esc(u.name)}</td><td>${t('role_' + u.role)}</td><td>${esc(u.login)}</td>${jur}</tr>`;
    }).join('');
    body = `<div class="card scroll"><table><tr>${th(['name', 'role', 'loginlbl', 'district', 'sector', 'cell', 'village'])}<th></th></tr>${rows}</table></div>
    <div class="card"><b>${t('createacct')}</b><div class="filters">
      <div><label>${t('fullname')}</label><input id="nu_n"></div>
      <div><label>${t('role')}</label><select id="nu_r"><option value="chw">${t('role_chw')}</option><option value="registrar">${t('role_registrar')}</option><option value="admin">${t('role_admin')}</option></select></div>
      <div><label>${t('phoneuser')}</label><input id="nu_l"></div>
      <div><label>${t('pin4')}</label><input id="nu_p" maxlength="4" inputmode="numeric"></div>
      <div><label>${t('district')}</label>${selD('nu', '')}</div>
      <div><label>${t('sector')}</label>${selS('nu', '', '')}</div>
      <div><label>${t('cellchw')}</label>${selC('nu', '', '', '')}</div>
      <div><label>${t('villagechw')}</label><input id="nu_v"></div></div>
      <button onclick="addUser()">${t('createacct')}</button></div>`;
  }
  return `<div class="greet"><div><div class="muted">${t('role_admin')}</div><h2>${esc(ME.name)}</h2></div></div>${tabs}${body}`;
}
async function addUser() {
  const db = DB(), v = id => G(id).value.trim(), login = v('nu_l'), pin = v('nu_p');
  if (!v('nu_n') || !login || !/^\d{4}$/.test(pin)) return toast(t('userbad'));
  if (db.users.some(u => u.login === login)) return toast(t('dup'));
  const role = v('nu_r'), geo = role === 'admin' ? { district: '', sector: '', cell: '', village: '' } : { district: G('nu_d').value, sector: G('nu_s').value, cell: role === 'chw' ? G('nu_c').value : '', village: role === 'chw' ? v('nu_v') : '' };
  if (role !== 'admin' && (!geo.district || !geo.sector || (role === 'chw' && !geo.cell))) return toast(t('needgeo'));
  db.users.push({ id: uid(), name: v('nu_n'), role, login, hash: await sha(login + ':' + pin), ...geo });
  logS(db, 'Account created: ' + login);
  S('rn_server', db);
  refreshCache();
  render();
  toast(t('created'));
}
function updUser(id) {
  const db = DB(), u = db.users.find(x => x.id === id);
  const pre = 'u_' + id, d = G(pre + '_d').value, sec = G(pre + '_s').value, cell = u.role === 'chw' ? G(pre + '_c').value : '';
  if (!d || !sec || (u.role === 'chw' && !cell)) return toast(t('needgeo'));
  u.district = d;
  u.sector = sec;
  if (u.role === 'chw') {
    u.cell = cell;
    u.village = G('uv_' + id).value.trim();
  }
  logS(db, `Jurisdiction updated for ${u.login}: ${u.district}/${u.sector}/${u.cell}/${u.village}`);
  S('rn_server', db);
  refreshCache();
  toast(t('savedok'));
}
function delUser(id) {
  const db = DB();
  db.users = db.users.filter(u => u.id !== id);
  S('rn_server', db);
  refreshCache();
  render();
}


/* ===== app.js: App shell and login ===== */
/* App shell: login (offline PIN), top bar, render loop */
let ME = null, KEY = null, TAB = '';

function toast(m) {
  const el = G('toast');
  el.textContent = m;
  el.classList.add('show');
  clearTimeout(toast.t);
  toast.t = setTimeout(() => el.classList.remove('show'), 3200);
}
const LOGO = '<span class="logo"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg></span>';
function renderBar() {
  G('bar').innerHTML = `<span class="brand">${LOGO}${t('app')}</span><span class="sp"></span>
  <button class="pill ${net() ? 'on' : 'off'}" onclick="toggleNet()" title="${t('nettip')}">${net() ? t('online') : t('offline')}</button>
  <select onchange="setLang(this.value)" aria-label="Language"><option value="en" ${lang === 'en' ? 'selected' : ''}>English</option>
    <option value="rw" ${lang === 'rw' ? 'selected' : ''}>Kinyarwanda</option></select>
  ${ME ? `<button class="ghost light" onclick="logout()">${t('logout')}</button>` : ''}`;
}
function loginHTML() {
  return `<section class="hero"><div class="logo big"><svg viewBox="0 0 24 24" width="30" height="30" fill="none" stroke="currentColor" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round">
    <path d="M5 12.5l4.5 4.5L19 7.5"/></svg></div><h1>${t('hero1')}</h1><p>${t('hero2')}</p>
    </section>
  <div class="card phone"><h2>${t('login')}</h2><label for="li">${t('user')}</label><input id="li" autocomplete="off">
    <label for="lp">${t('pin')}</label><input id="lp" type="password" inputmode="numeric" maxlength="4" onkeydown="if(event.key==='Enter')doLogin()">
    <div class="err" id="le"></div><button style="width:100%" onclick="doLogin()">${t('login')}</button>
    </div>
  <p class="muted center">${t('accnote')}</p>`;
}
async function doLogin() {
  const id = G('li').value.trim(), pin = G('lp').value;
  const u = J('rn_cred', []).find(x => x.login === id);
  if (!u || u.hash !== await sha(id + ':' + pin)) {
    G('le').textContent = t('wrongcred') + (net() ? '' : t('wrongoff'));
    return;
  }
  ME = u;
  KEY = await deriveKey(pin, 'rn:' + u.id);
  W = null;
  MODAL = null;
  TAB = u.role === 'chw' ? '' : 'dash';
  render();
  sync();
}
function logout() {
  ME = KEY = W = MODAL = null;
  render();
}
function toggleNet() {
  LS.setItem('rn_net', net() ? 'off' : 'on');
  refreshCache();
  render();
  if (net()) sync();
}
function setLang(l) {
  lang = l;
  LS.setItem('rn_lang', l);
  document.documentElement.lang = l;
  render();
}

async function render() {
  renderBar();
  document.body.dataset.role = ME ? ME.role : '';
  const app = G('app');
  if (!ME) {
    app.innerHTML = loginHTML();
    return;
  }
  if (ME.role === 'chw') {
    const h = await chwHTML();
    if (ME) app.innerHTML = h;
    else render();
  }
  else if (!net()) app.innerHTML = `<div class="card phone"><h3>${t('offtitle')}</h3><p>${t('offtext')}</p></div>`;
  else app.innerHTML = ME.role === 'registrar' ? regHTML() : admHTML();
  labelTables();
}
/* Copy each column heading onto its cells so tables can turn into labelled cards on phones (see styles.css) */
function labelTables() {
  document.querySelectorAll('#app table').forEach(tb => {
    const head = [...tb.rows].find(r => r.querySelector('th'));
    if (!head) return;
    head.classList.add('thead');
    const names = [...head.cells].map(c => c.textContent.trim());
    [...tb.rows].forEach(r => {
      if (r === head) return;
      [...r.cells].forEach((c, i) => { if (names[i] && c.colSpan === 1) c.dataset.label = names[i]; });
    });
  });
}

setInterval(() => { if (ME && ME.role === 'chw') sync(); }, 4000);
document.documentElement.lang = lang;
seed().then(() => { refreshCache(); render(); });
</script>
</body>
</html>
'''

# ---------------------------------------------------------------------------
# Database (SQLite key/value store holding the shared server state as JSON)
# ---------------------------------------------------------------------------
def connect():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    return conn


def load_state():
    with LOCK, closing(connect()) as conn:
        row = conn.execute("SELECT value FROM kv WHERE key = 'server'").fetchone()
        return row[0] if row else None


def save_state(text):
    with LOCK, closing(connect()) as conn, conn:
        conn.execute("INSERT OR REPLACE INTO kv (key, value) VALUES ('server', ?)", (text,))


def reset_state():
    with LOCK, closing(connect()) as conn, conn:
        conn.execute("DELETE FROM kv")


# ---------------------------------------------------------------------------
# HTTP server
# ---------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body=b"", ctype="application/json; charset=utf-8"):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/":
            path = "/index.html"
        if not path.startswith("/api/"):
            root = os.path.dirname(os.path.abspath(__file__))
            fpath = os.path.normpath(os.path.join(root, path.lstrip("/")))
            types = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
                     ".js": "text/javascript; charset=utf-8", ".png": "image/png", ".jpg": "image/jpeg",
                     ".ico": "image/x-icon", ".svg": "image/svg+xml"}
            ctype = types.get(os.path.splitext(fpath)[1].lower())
            if fpath.startswith(root + os.sep) and ctype and os.path.isfile(fpath):
                with open(fpath, "rb") as f:
                    return self._send(200, f.read(), ctype)
            return self._send(404, '{"error": "not found"}')
        elif path == "/api/ping":
            self._send(200, '{"ok": true}')
        elif path == "/api/db":
            state = load_state()
            if state is None:
                self._send(404, '{"error": "empty"}')
            else:
                self._send(200, state)
        else:
            self._send(404, '{"error": "not found"}')

    def do_POST(self):
        path = self.path.split("?")[0]
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            return self._send(413, '{"error": "too large"}')
        raw = self.rfile.read(length)
        if path == "/api/db":
            try:
                data = json.loads(raw)
                assert isinstance(data, dict) and "users" in data and "records" in data
            except (ValueError, AssertionError):
                return self._send(400, '{"error": "invalid database"}')
            save_state(json.dumps(data))
            self._send(200, '{"ok": true}')
        elif path == "/api/reset":
            reset_state()
            self._send(200, '{"ok": true}')
        else:
            self._send(404, '{"error": "not found"}')

    def log_message(self, fmt, *args):
        if "/api/" not in self.path:
            print("  %s - %s" % (self.address_string(), fmt % args))


def lan_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def main():
    parser = argparse.ArgumentParser(description="Registration National prototype server")
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8000)))
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print("Registration National is running")
    print("  Local:   http://127.0.0.1:%d" % args.port)
    if args.host == "0.0.0.0":
        print("  Network: http://%s:%d" % (lan_ip(), args.port))
    print("  Data:    %s" % DB_FILE)
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
