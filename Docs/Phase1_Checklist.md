# Phase 1 Completion Checklist

**Project:** TinyTelemetry Protocol v1
**Team:** [Your Team Name]
**Due:** Week 7

---

## ✅ DELIVERABLES STATUS

### 1. Project Proposal (Max 3 pages)
- [x] **File created:** `Docs/Proposal.md`
- [ ] **Content review:**
  - [ ] Assigned scenario clearly stated (IoT Telemetry Protocol)
  - [ ] Short motivation explaining why this protocol is needed
  - [ ] Proposed protocol approach described
  - [ ] Team members listed
- [ ] **Export to PDF:** `Docs/Proposal.pdf`
- [ ] **Upload to LMS**

### 2. Mini-RFC Draft (Sections 1-3)
- [x] **File created:** `Docs/Mini_RFC_Draft.md`
- [ ] **Content review:**
  - [x] Section 1: Introduction (purpose, motivation, use case, constraints)
  - [x] Section 2: Protocol Architecture (entities, FSM, communication model)
  - [x] Section 3: Message Formats (header table + sample messages)
  - [x] Header table with byte offsets included
  - [x] Sample message in hex provided
  - [x] Pack format (struct.pack) documented
- [ ] **Export to PDF:** `Docs/Mini_RFC_Draft.pdf`
- [ ] **Upload to LMS**

### 3. Working Prototype
- [x] **Server implementation:** `src/server.py`
  - [x] UDP socket listener
  - [x] Parse header correctly
  - [x] Log received packets to console
  - [x] Per-device state tracking
  - [x] Duplicate detection
  - [x] Sequence gap detection

- [x] **Client implementation:** `src/client.py`
  - [x] Sends INIT message on startup
  - [x] Sends DATA messages periodically
  - [x] Proper header encoding
  - [x] JSON payload with temperature/humidity

- [x] **Protocol module:** `src/protocol.py`
  - [x] pack_header() function
  - [x] unpack_header() function
  - [x] Message type constants
  - [x] Helper functions

- [ ] **Local testing:**
  - [ ] Run server successfully
  - [ ] Run client successfully
  - [ ] Verify INIT message received
  - [ ] Verify DATA messages received
  - [ ] Check logs show correct sequence numbers
  - [ ] No crashes or errors

### 4. README with Instructions
- [x] **File created:** `README.txt`
- [ ] **Content review:**
  - [x] Clear instructions to run server
  - [x] Clear instructions to run client
  - [x] System requirements listed
  - [x] Expected output examples
  - [x] Troubleshooting section
  - [ ] Demo video link added (see item 5)
- [ ] **Verify instructions work** (test on fresh terminal)
- [ ] **Upload to LMS**

### 5. Demo Video (5 minutes max)
- [ ] **Record video showing:**
  - [ ] Team member introduction
  - [ ] Explain protocol header fields and their lengths
  - [ ] Show protocol.py code (header format)
  - [ ] Start server in one terminal
  - [ ] Start client in another terminal
  - [ ] Show INIT message in server logs
  - [ ] Show DATA messages in server logs
  - [ ] Explain sequence numbers
  - [ ] Show baseline test script execution
  - [ ] Total duration ≤ 5 minutes

- [ ] **Upload to YouTube/Google Drive/OneDrive**
  - [ ] Set access to "Anyone with the link can view"
  - [ ] Test link in incognito/private browser
  - [ ] Add link to README.txt
  - [ ] Add link to LMS submission

### 6. Baseline Test Script
- [x] **File created:** `tests/baseline_test.sh`
- [x] **Script made executable:** `chmod +x`
- [ ] **Test execution:**
  - [ ] Script runs without errors
  - [ ] Creates log directory with timestamp
  - [ ] Runs client for 60 seconds
  - [ ] Generates server.log and client.log
  - [ ] Reports statistics correctly
  - [ ] Shows PASS result (≥99% delivery)
- [ ] **Upload logs/** directory to LMS (example run)

---

## 📋 ACCEPTANCE CRITERIA VERIFICATION

Based on Phase 1 requirements:

| Criterion | Status | Notes |
|-----------|--------|-------|
| Proposal clarity | ⏳ Pending review | Check motivation is concise |
| Feasibility demonstrated | ✅ Done | Code implemented |
| Initial message format correctness | ✅ Done | 10-byte header matches spec |
| Code runs locally | ⏳ Needs testing | Test on fresh terminal |
| Logs present | ✅ Done | Server prints to console |
| Demo video link works | ❌ Not created | Record this week |
| Prototype demonstrates INIT | ✅ Done | Client sends INIT on start |
| Prototype demonstrates DATA | ✅ Done | Client sends periodic DATA |

---

## 🎯 TESTING CHECKLIST

### Manual Testing (Before Recording Video)

```bash
# Terminal 1: Start server
cd /Users/yousseftarek/Documents/iot-project/iot-project/src
python3 server.py

# Terminal 2: Start client (in separate window)
cd /Users/yousseftarek/Documents/iot-project/iot-project/src
python3 client.py

# Expected: See INIT followed by DATA messages in server terminal
# Expected: No errors, clean output
```

### Baseline Test Execution

```bash
cd /Users/yousseftarek/Documents/iot-project/iot-project/tests
./baseline_test.sh

# Expected output:
# - "Test Result: PASS"
# - Total packets: ~61
# - Success rate: ≥99%
```

---

## 📦 SUBMISSION PACKAGE

Create a ZIP file with:

```
Phase1_TinyTelemetry_[TeamName].zip
├── README.txt (with video link)
├── Docs/
│   ├── Proposal.pdf
│   └── Mini_RFC_Draft.pdf
├── src/
│   ├── protocol.py
│   ├── server.py
│   └── client.py
├── tests/
│   └── baseline_test.sh
└── logs/
    └── baseline_[timestamp]/
        ├── server.log
        └── client.log
```

---

## ⚠️ FINAL PRE-SUBMISSION CHECKS

- [ ] All team members' names in proposal
- [ ] All files use UTF-8 encoding
- [ ] No hardcoded absolute paths in code
- [ ] Video is accessible (test in incognito mode)
- [ ] README has working video link
- [ ] Code runs on macOS (tested)
- [ ] Code runs on Linux (if available to test)
- [ ] Spell-check all documents
- [ ] Consistent naming (TinyTelemetry vs Tiny Telemetry)
- [ ] All required sections in Mini-RFC (1-3 only)
- [ ] Proposal is ≤3 pages when exported to PDF

---

## 📅 SUGGESTED TIMELINE

**5 days before deadline:**
- [ ] Complete all code testing
- [ ] Finalize proposal and Mini-RFC text
- [ ] Export documents to PDF

**3 days before deadline:**
- [ ] Record demo video
- [ ] Upload and get shareable link
- [ ] Add link to README

**2 days before deadline:**
- [ ] Run final baseline test
- [ ] Create submission ZIP
- [ ] Test extraction and verify all files present

**1 day before deadline:**
- [ ] Submit to LMS
- [ ] Verify submission successful
- [ ] Backup copy of all files

---

## 📧 TEAM COORDINATION

**Assign responsibilities:**

- [ ] Person 1: Proposal writing + review
- [ ] Person 2: Mini-RFC sections 1-3
- [ ] Person 3: Code testing + baseline script
- [ ] Person 4: Demo video recording + editing

**Communication:**
- Set up team chat (WhatsApp/Discord/Slack)
- Daily check-ins during final week
- Shared Google Drive/Dropbox for documents

---

**Last Updated:** [Date]
**Completed By:** [Names]
