5. Project Timeline & Phases (detailed)
1. Phase 1 — Prototype (Due: Week 7)
Deliverables (upload to LMS):
• Project proposal (max 3 pages) including: assigned scenario, short motivation, and
proposed protocol approach.
• Mini-RFC draft (sections 1–3): Introduction, Protocol Architecture, Message Formats
(header table + sample message).
• Working prototype demonstrating INIT and DATA exchanges over UDP (server + client).
• README with instructions to run locally and a 5-minute demo video uploaded online
(Just make sure that its access is set to “anyone with the link can view”). Only submit the
video link inside the README.txt file and make sure that it’s working.
• Automated script to run the 'Baseline local' test scenario for your assigned project.
Checklist: proposal clarity, feasibility, initial message format correctness, code runs locally,
logs present, demo video link, prototype demonstrates core functionality.
2. Phase 2 — Feature Completion & Tests (Due: Week 12)
Deliverables:
• Full implementation of mandatory scenario-specific features and handling of error
cases.
• Evidence of running required test scenarios: logs, pcap traces, netem command list, and
raw measurement CSVs.
• Updated Mini-RFC with sections 4–7 (procedures, reliability, experimental plan).
Checklist: mandatory features pass acceptance criteria, logs show tests, pcap snippets
included.
3. Phase 3— Final Report & Presentation (Due: Week 14)
Deliverables:
• Final Mini-RFC (5–8 pages), full code repository with commit history, and reproducible
scripts.
• Technical report (6–8 pages) that includes methodology, detailed plots, interpretation,
and limitations.
• Presentation slides (8–10) and final demo video (≤10 minutes) uploaded online (Just
make sure that its access is set to “anyone with the link can view”). Only submit the
video link inside the README.txt file and make sure that it’s working.
Checklist: report quality, reproducibility, comparison with baseline, and presentation
clarity.
• Some key points to be covered in video demo:
• Explain your protocol header fields and why you chose their length.
• How does your protocol handle packet loss and reordering?
• Show an excerpt from your pcap that illustrates retransmission or recovery.
• Explain one experiment you ran and why the results look the way they do.
6. Mini-RFC Template:
Students must submit a Mini-RFC following this structure. Use exact headings and include
required subsections. Below we give expanded guidance and examples.
1. Introduction
Brief description of protocol, use case, and why a new protocol is needed. State assumptions
and constraints (e.g., max packet size, allowed loss).
2. Protocol Architecture
Describe entities, sequence flows, and provide a finite-state machine (FSM). Include
diagrams (png/svg) or ASCII diagrams in the appendix. Example: Client -> Server
sessionless telemetry vs sessionful file-transfer.
3. Message Formats
Provide a header field table. Example (IoT telemetry header):
Example: IoT Telemetry Header (total 10 bytes):
Field | Size (bits) | Description
---
Version | 4 | Protocol version
MsgType | 4 | Message type (0=INIT,1=DATA,2=ACK,3=ERROR)
DeviceID | 16 | Unique device id
SeqNum | 16 | Sequence number
Timestamp | 32 | Unix epoch seconds (or milliseconds truncated)
Flags | 8 | Flags for batching/priority
Students should provide byte offsets and struct packing format (e.g., struct.pack('!B B H H I
B', ...)) for each header. If using variable-length payloads, document length fields and
fragmentation rules.
4. Communication Procedures
Describe session start, normal data exchange, error recovery, and shutdown. Provide
example step-by-step sequences.
5. Reliability & Performance Features
Explain retransmission strategy, timeout selection, windowing, or other techniques like
FEC. If using timers, show how they were calculated (e.g., RTO = estimate_RTT + 4 *
dev_RTT).
6. Experimental Evaluation Plan
Specify baselines, metrics, measurement methods, and how to simulate network conditions.
Include exact netem commands for Linux and alternatives for other OSes. Provide scripts to
automate runs and collect results.
7. Example Use Case Walkthrough
Provide an end-to-end trace example (timestamps, messages sent/received) for a single
session. Include pcap excerpt (as appendix) and explanation.
8. Limitations & Future Work
Honest assessment of weaknesses and potential improvements; essential for high marks.
9. References
Reference any RFCs, papers, or libraries used. Include links or RFC numbers where
applicable.
7. Originality and Academic Integrity
Each team must design an original protocol. Submissions will be checked for similarity against
public repositories and AI-generated samples.
Your design must include:
1. A unique protocol name and version field.
2. At least two original mechanisms or field definitions, such as a timestamp encoding,
field/data compression, or adaptive update rate.
3. A justification section in your Mini-RFC explaining how your design differs from known
protocols (e.g., MQTT-SN).
4. No reuse of external networking/game libraries (e.g., ENet, RakNet, Lidgren).
Only standard socket and serialization libraries are allowed.
Submissions that substantially replicate public code or lack experimental justification will not
receive credit.
8. Appendices
1. Appendix A — Example netem commands (Linux)
Replace <IF> with your interface (e.g., eth0 or lo for loopback):
- Add 5% loss: sudo tc qdisc add dev <IF> root netem loss 5%
- Add 100ms delay with 10ms jitter: sudo tc qdisc add dev <IF> root netem delay 100ms
10ms
- Combine rate and delay (tbf + netem):
sudo tc qdisc add dev <IF> root handle 1: tbf rate 2mbit burst 32k latency 400ms
sudo tc qdisc add dev <IF> parent 1:1 netem delay 50ms
- Remove qdisc: sudo tc qdisc del dev <IF> root
2. Appendix B — Reproducible experiment checklist (recommended)
• Provide a script ./run_experiment.sh that sets up netem (optional) and runs the
client/server for a single test.
• Store raw outputs (pcap, CSV) in a directory labeled with timestamp and seed.
• Provide a Jupyter notebook or Python script that loads CSVs and reproduces the plots in
the report.
• Document exact commands and environment (OS, Python version, library versions).
