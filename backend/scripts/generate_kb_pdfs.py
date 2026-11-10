# backend/scripts/generate_kb_pdfs.py
import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
)

OUTPUT_DIR = "./data/kb_pdfs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

NAVY_HEADER = colors.HexColor("#163A5F")
TEAL_TITLE = colors.HexColor("#2E6B8E")
AMBER_BG = colors.HexColor("#FFF6D6")
AMBER_TEXT = colors.HexColor("#7A3E00")
ROW_ALT = colors.HexColor("#F4F7FA")
BORDER_GRAY = colors.HexColor("#8A9BA8")

def get_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="OrgSubHeader", fontName="Helvetica-Bold", fontSize=11,
        leading=14, alignment=1, textColor=TEAL_TITLE, spaceAfter=6
    ))
    styles.add(ParagraphStyle(
        name="DocTitle", fontName="Helvetica-Bold", fontSize=20,
        leading=24, alignment=1, textColor=NAVY_HEADER, spaceAfter=6
    ))
    styles.add(ParagraphStyle(
        name="DocSub", fontName="Times-Roman", fontSize=13,
        leading=16, alignment=1, textColor=colors.HexColor("#555555"), spaceAfter=14
    ))
    styles.add(ParagraphStyle(
        name="ItalicNote", fontName="Times-Italic", fontSize=10,
        leading=13, alignment=1, textColor=colors.HexColor("#666666"), spaceBefore=10
    ))
    styles.add(ParagraphStyle(
        name="SectionH1", fontName="Helvetica-Bold", fontSize=14,
        leading=18, textColor=NAVY_HEADER, spaceBefore=14, spaceAfter=6
    ))
    styles.add(ParagraphStyle(
        name="SectionH2", fontName="Helvetica-Bold", fontSize=11,
        leading=14, textColor=TEAL_TITLE, spaceBefore=10, spaceAfter=4
    ))
    styles.add(ParagraphStyle(
        name="BodySerif", fontName="Times-Roman", fontSize=10,
        leading=14, textColor=colors.black, spaceAfter=4
    ))
    styles.add(ParagraphStyle(
        name="SafetyBox", fontName="Times-Bold", fontSize=9.5,
        leading=13, textColor=AMBER_TEXT, backColor=AMBER_BG,
        borderPadding=8, spaceBefore=10, spaceAfter=10
    ))
    styles.add(ParagraphStyle(
        name="TableHeader", fontName="Helvetica-Bold", fontSize=9.5,
        leading=12, textColor=colors.white
    ))
    styles.add(ParagraphStyle(
        name="TableCell", fontName="Times-Roman", fontSize=9.5,
        leading=12, textColor=colors.black
    ))
    return styles

def make_two_col_table(rows_data, styles, col_widths=(2.1*inch, 4.4*inch)):
    formatted_rows = []
    for i, (col1, col2) in enumerate(rows_data):
        style = styles["TableHeader"] if i == 0 else styles["TableCell"]
        formatted_rows.append([Paragraph(col1, style), Paragraph(col2, style)])
    
    t = Table(formatted_rows, colWidths=col_widths, repeatRows=1)
    ts = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY_HEADER),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.6, BORDER_GRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ])
    for r in range(1, len(rows_data)):
        if r % 2 == 1:
            ts.add("BACKGROUND", (0, r), (-1, r), ROW_ALT)
    t.setStyle(ts)
    return t

def build_kb_pdf(doc_spec: dict):
    styles = getSampleStyleSheet()
    custom_styles = get_styles()
    filepath = os.path.join(OUTPUT_DIR, f"{doc_spec['doc_id']}.pdf")
    
    doc = SimpleDocTemplate(
        filepath, pagesize=A4,
        leftMargin=0.8*inch, rightMargin=0.8*inch,
        topMargin=0.75*inch, bottomMargin=0.75*inch
    )
    story = []

    def add_header_footer(canvas, doc_obj):
        canvas.saveState()
        canvas.setFont("Helvetica", 8.5)
        canvas.setFillColor(colors.HexColor("#666666"))
        header_text = f"ABC Digital Services (ADS) | {doc_spec['doc_id']}"
        canvas.drawRightString(A4[0] - 0.8*inch, A4[1] - 0.45*inch, header_text)
        canvas.setFont("Times-Roman", 9.5)
        canvas.setFillColor(colors.black)
        canvas.drawCentredString(A4[0] / 2.0, 0.45*inch, str(doc_obj.page))
        canvas.restoreState()

    # --- PAGE 1: COVER PAGE ---
    story.append(Spacer(1, 0.4*inch))
    story.append(Paragraph("ABC DIGITAL SERVICES", custom_styles["OrgSubHeader"]))
    story.append(Paragraph(doc_spec["title"], custom_styles["DocTitle"]))
    story.append(HRFlowable(width="100%", thickness=1, color=TEAL_TITLE, spaceAfter=8))
    story.append(Paragraph("Approved IT Knowledge Article Pack", custom_styles["DocSub"]))

    cov_t1 = [
        [Paragraph(h, custom_styles["TableHeader"]) for h in ["Document ID", "Version", "Status", "Effective date"]],
        [Paragraph(v, custom_styles["TableCell"]) for v in [doc_spec["doc_id"], "1.0", "Approved for capstone use", "06 Nov 2026"]]
    ]
    t1 = Table(cov_t1, colWidths=[1.625*inch]*4)
    t1.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY_HEADER),
        ("GRID", (0, 0), (-1, -1), 0.6, BORDER_GRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t1)
    story.append(Spacer(1, 12))

    cov_t2 = [
        [Paragraph(h, custom_styles["TableHeader"]) for h in ["Knowledge owner", "Review cycle", "Classification", "Issue category"]],
        [Paragraph(v, custom_styles["TableCell"]) for v in [doc_spec["owner"], "Every 6 months", "Internal", doc_spec["category"]]]
    ]
    t2 = Table(cov_t2, colWidths=[1.625*inch]*4)
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY_HEADER),
        ("GRID", (0, 0), (-1, -1), 0.6, BORDER_GRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t2)
    story.append(Paragraph("Fictional organization and sample operating procedures", custom_styles["ItalicNote"]))
    story.append(PageBreak())

    # --- PAGE 2+: HOW TO USE & RETRIEVAL METADATA ---
    story.append(Paragraph("How to use this article", custom_styles["SectionH1"]))
    story.append(Paragraph(
        "This document is authoritative only for the fictional ABC Digital Services (ADS) capstone "
        "environment. The assistant may explain and recommend these steps, but must not execute privileged "
        "actions, approve expenditure, change access, or close a case on the user's behalf.",
        custom_styles["BodySerif"]
    ))
    story.append(Spacer(1, 6))

    meta_rows = [
        ("Retrieval metadata", "Value"),
        ("Document ID", doc_spec["doc_id"]),
        ("Category", doc_spec["category"]),
        ("Products / assets", doc_spec["products"]),
        ("Platform", doc_spec["platform"]),
        ("Approval status", "Approved"),
        ("Effective date", "06 Nov 2026"),
        ("Superseded by", "None"),
    ]
    story.append(make_two_col_table(meta_rows, custom_styles))
    story.append(Paragraph(
        "Safety boundary: Never request passwords, MFA codes, recovery keys, private keys, or full "
        "payment-card data. Stop and escalate if there is smoke, swelling, electric shock, suspected "
        "compromise, or possible data loss.",
        custom_styles["SafetyBox"]
    ))

    # --- SECTIONS 1 TO 4 ---
    for idx, sec in enumerate(doc_spec["sections"], start=1):
        story.append(Paragraph(f"{idx}. {sec['heading']}", custom_styles["SectionH1"]))
        guidance_rows = [
            ("Field", "Guidance"),
            ("Common user phrases", sec["phrases"]),
            ("Default priority", sec["priority"]),
            ("Objective", sec["objective"]),
            ("Minimum intake", sec["intake"]),
        ]
        story.append(make_two_col_table(guidance_rows, custom_styles))
        story.append(Paragraph("Procedure", custom_styles["SectionH2"]))
        for step_num, step_text in enumerate(sec["procedure"], start=1):
            story.append(Paragraph(f"<b>{step_num}.</b> {step_text}", custom_styles["BodySerif"]))
        story.append(Paragraph("Resolution and escalation", custom_styles["SectionH2"]))
        res_rows = [
            ("Outcome", "Criteria"),
            ("Resolve when", sec["resolve_when"]),
            ("Escalate when", sec["escalate_when"]),
            ("Evidence to record", sec["evidence"]),
            ("Forbidden actions", sec["forbidden"]),
        ]
        story.append(make_two_col_table(res_rows, custom_styles))
        story.append(Spacer(1, 10))

    # --- GENERAL TICKET RULES & REFERENCE BASIS ---
    story.append(Paragraph("General ticket handling rules", custom_styles["SectionH1"]))
    priority_rows = [
        ("Priority", "Use when"),
        ("P1 Critical", "Widespread outage, active security threat, severe safety risk, or executive-critical service unavailable. Page the major-incident or security team immediately."),
        ("P2 High", "User cannot perform time-critical work and no practical workaround exists. Target assignment within 30 minutes."),
        ("P3 Normal", "Single-user degradation or standard fulfillment request. Target assignment within 4 business hours."),
        ("P4 Low", "Information request, planned change, or non-urgent accessory request. Target assignment within 1 business day."),
    ]
    story.append(make_two_col_table(priority_rows, custom_styles))
    story.append(Paragraph("Standard ticket record", custom_styles["SectionH2"]))
    story.append(Paragraph(
        "Record requestor, business justification, device or application, asset tag where applicable, location, "
        "symptoms, error text, start time, impact, troubleshooting attempted, approvals, evidence, result, and "
        "next owner. Do not paste secrets or unnecessary personal data.",
        custom_styles["BodySerif"]
    ))
    story.append(Paragraph("Knowledge quality and review", custom_styles["SectionH2"]))
    story.append(Paragraph(
        "The knowledge owner reviews this article every six months and after any major process, product, "
        "security, or supplier change. Superseded versions must be excluded from retrieval. Conflicts are "
        "resolved in favor of the newest approved article; otherwise the assistant must disclose the conflict and "
        "recommend escalation.",
        custom_styles["BodySerif"]
    ))
    story.append(Paragraph("Reference basis", custom_styles["SectionH1"]))
    refs = [
        "Secure AI Troubleshooting Assistant BRD v1.0: approved content, metadata, ordered guidance, citations, verification, safe fallback, and escalation.",
        "NIST SP 800-61 Rev. 3 (2025): Detect, Respond, Recover, and continuous improvement concepts for security-related incidents.",
        "Microsoft Intune and Windows Autopilot documentation: managed application deployment, device enrollment, assignment, and lifecycle practices.",
        "ITIL-aligned service management practices: incident, request, change, asset, and knowledge management concepts."
    ]
    for r in refs:
        story.append(Paragraph(f"• {r}", custom_styles["BodySerif"]))

    doc.build(story, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
    print(f"Generated: {filepath}")


# Append to backend/scripts/generate_kb_pdfs.py

KB_ARTICLES = [
    # 1. EXACT REPLICA OF SCREENSHOTS (Updated to ABC Digital Services / ADS)
    {
        "doc_id": "ADS-KB-ASSET-001",
        "title": "Secondary Laptop Allocation and Return",
        "owner": "IT Service Management",
        "category": "IT asset allocation",
        "products": "secondary laptop, loaner, extension, return, reassignment, lost, stolen",
        "platform": "Windows 11, Microsoft 365, managed enterprise endpoints",
        "sections": [
            {
                "heading": "Request a secondary laptop",
                "phrases": '"need a second laptop", "project device", "client laptop required"',
                "priority": "P4 Low; P2/P3 when primary device failed",
                "objective": "Allocate only where a documented business, technical, client, or continuity need exists.",
                "intake": "Business justification; project/client; duration; required build; data classification; manager, cost centre, asset custodian; primary asset.",
                "procedure": [
                    "Confirm why the primary device cannot meet the requirement. Examples include segregated client environment, incompatible build, controlled testing, or temporary continuity.",
                    "Check for alternatives such as virtual desktop, test VM, loaner pool, or approved shared lab that reduce asset and security risk.",
                    "Obtain manager approval, project/budget approval, and information-security or client approval when segregation or sensitive data is involved.",
                    "Reserve an available compliant device from inventory. Record asset tag, serial, configuration, custodian, purpose, issue date, and return date.",
                    "Provision with the approved image, encryption, endpoint protection, patching, least-privilege access, and only required applications.",
                    "Have the user acknowledge acceptable use, physical security, no sharing, reporting obligations, and return date.",
                    "Validate enrollment and compliance before handover. Schedule reminders before expiry."
                ],
                "resolve_when": "Device is compliant, assigned in the asset register, acknowledged, and linked to an expiry date.",
                "escalate_when": "No inventory; unclear justification; client/security approval missing; incompatible data jurisdiction; user already holds multiple unreviewed devices.",
                "evidence": "Approvals, alternatives considered, asset/serial, compliance, issue/return dates, acknowledgment.",
                "forbidden": "Issuing an unmanaged device; sharing credentials; bypassing encryption; indefinite allocation without review."
            },
            {
                "heading": "Extend a secondary-laptop allocation",
                "phrases": '"extend loaner", "keep second laptop longer", "project extended"',
                "priority": "P4 Low",
                "objective": "Extend only after revalidating need, compliance, ownership, and return date.",
                "intake": "Asset tag; current expiry; revised project end; justification; manager/project owner; compliance status; physical location.",
                "procedure": [
                    "Review the original request, current custodian, purpose, expiry, and any overdue notices.",
                    "Confirm the business need continues and obtain a revised end date. Open-ended dates are not permitted for temporary allocations.",
                    "Check device compliance, patch age, encryption, endpoint protection, warranty, last check-in, and asset location.",
                    "Confirm manager and project/budget approval. Obtain security/client reapproval if the original basis or data handling changed.",
                    "Update the asset register and send the user the new return date and conditions.",
                    "If compliance cannot be verified, suspend the extension and arrange device check-in, replacement, or return."
                ],
                "resolve_when": "New expiry and approvals are recorded, and the device is compliant.",
                "escalate_when": "Device overdue; no check-in; user changed role; project ended; security posture failed; asset location unknown.",
                "evidence": "Original and revised expiry, approvals, compliance snapshot, location, notification.",
                "forbidden": "Backdating approval; extending indefinitely; remotely weakening compliance controls."
            },
            {
                "heading": "Return or reassign a secondary laptop",
                "phrases": '"return loaner", "transfer project laptop", "give laptop to teammate"',
                "priority": "P3 Normal",
                "objective": "Protect data and chain of custody before return, wipe, or reassignment.",
                "intake": "Asset tag; current custodian; return/reassignment reason; target office; data backup status; accessories.",
                "procedure": [
                    "Instruct the current user not to hand the device directly to another employee. All transfers go through IT asset custody.",
                    "Confirm corporate data is synchronized to the approved storage location and that local-only data requiring retention is identified.",
                    "Collect device, charger, dock, and tracked accessories. Inspect condition and record custody time and location.",
                    "Remove user assignment and access through approved processes. Perform the approved secure wipe or rebuild before reassignment.",
                    "Run hardware diagnostics, apply updates, verify encryption and enrollment, and update the asset register.",
                    "For reassignment, create a new custody record and user acknowledgment. For retirement, follow disposal documentation."
                ],
                "resolve_when": "Custody, wipe/rebuild, condition, inventory, and new disposition are documented.",
                "escalate_when": "Device missing; data cannot be synchronized; legal hold; suspected compromise; damage; wipe failure.",
                "evidence": "Custody record, accessories, backup confirmation, wipe/rebuild result, new owner/disposition.",
                "forbidden": "Peer-to-peer handoff; deleting data before legal/retention check; reassignment without wipe."
            },
            {
                "heading": "Lost or stolen laptop",
                "phrases": '"laptop missing", "device stolen", "left laptop in taxi"',
                "priority": "P1/P2 Security incident",
                "objective": "Contain risk rapidly while preserving accurate incident evidence.",
                "intake": "Asset tag if known; user; last known time/place; whether powered on; sensitive data; travel/client context; police report if applicable.",
                "procedure": [
                    "Tell the user to report immediately to the service desk and security team. Do not delay while searching extensively.",
                    "Collect minimum facts without asking for passwords or MFA codes. Create a security incident and link the asset record.",
                    "Security or endpoint administrators may use approved tools to lock, retire, locate, or wipe the device according to policy and legal approval. The assistant must only recommend escalation.",
                    "Reset or revoke sessions and credentials only through the identity/security incident process based on assessed risk.",
                    "Ask the user to preserve travel receipts, location details, and police/report references where required. Do not encourage personal confrontation or recovery attempts.",
                    "Arrange a replacement or loaner after manager/security authorization. Complete lessons learned and inventory disposition."
                ],
                "resolve_when": "Security confirms containment, asset status is recorded, and replacement/access recovery is managed.",
                "escalate_when": "Always escalate immediately; higher urgency for regulated/client data, active sessions, or suspected targeted theft.",
                "evidence": "Incident ID, asset, timeline, location, data classification, containment actions by authorized teams.",
                "forbidden": "User self-tracking or confronting a suspect; disclosing location data broadly; remote actions by unauthorized staff."
            }
        ]
    },

    # 2. CORPORATE VPN & NETWORK CONNECTIVITY
    {
        "doc_id": "ADS-KB-NET-002",
        "title": "Corporate VPN Connectivity and Split-Tunnel Troubleshooting",
        "owner": "Network Operations",
        "category": "Network & VPN",
        "products": "Always-On VPN, Error 809, IKEv2, certificate auth, split-tunnel, internal DNS",
        "platform": "Windows 11, macOS Sequoia, Cisco AnyConnect / Windows Always-On VPN",
        "sections": [
            {
                "heading": "Resolve VPN Error 809 (UDP 500/4500 blocked)",
                "phrases": '"VPN error 809", "network connection between computer and VPN server could not be established"',
                "priority": "P2 High when blocking remote work; P3 Normal otherwise",
                "objective": "Restore IKEv2 tunnel negotiation or fail over to TLS 443 cleanly.",
                "intake": "Asset tag; user ISP/hotel network; VPN gateway hostname; error code; local firewall status.",
                "procedure": [
                    "Verify the user has working external internet connectivity by testing public HTTPS sites.",
                    "Check if the user is on a restricted guest Wi-Fi or mobile hotspot blocking UDP ports 500 and 4500 required for IKEv2.",
                    "Run network diagnostics against vpn-gw-01.ads.local on TCP port 443 and verify gateway latency.",
                    "Instruct user to switch the ADS VPN client profile from 'Automatic (IKEv2)' to 'SSTP / TLS 443 Fallback'.",
                    "Flush local DNS resolver cache (`ipconfig /flushdns`) and re-test internal intranet reachability."
                ],
                "resolve_when": "VPN tunnel establishes, internal corp DNS resolves, and latency is below 150ms.",
                "escalate_when": "Both IKEv2 and TLS 443 fail; gateway health check reports DEGRADED; user device certificate is revoked.",
                "evidence": "Gateway probe result, protocol used, ISP type, DNS test confirmation.",
                "forbidden": "Instructing user to disable Windows Defender Firewall globally; sharing static VPN pre-shared keys."
            },
            {
                "heading": "Renew expired machine certificate for VPN authentication",
                "phrases": '"VPN certificate expired", "no valid client certificate found", "Error 798"',
                "priority": "P3 Normal",
                "objective": "Renew enterprise PKI machine certificate via Intune/Auto-Enrollment.",
                "intake": "Asset tag; certificate thumbprint expiry date; current network connection.",
                "procedure": [
                    "Connect via the temporary TLS bootstrap profile or corporate office LAN.",
                    "Trigger Intune Company Portal sync or run `certutil -pulse` in a standard terminal.",
                    "Verify the new ADS-Endpoint-Auth certificate appears under Local Machine Personal Certificates.",
                    "Disconnect bootstrap profile and reconnect via primary Always-On VPN tunnel."
                ],
                "resolve_when": "New PKI certificate is valid and primary VPN connects automatically.",
                "escalate_when": "Device is dropped from Active Directory trust or Intune MDM enrollment is broken.",
                "evidence": "Certificate expiration date, Intune sync timestamp, tunnel status.",
                "forbidden": "Exporting private keys (.pfx) across machines; installing untrusted root certificates."
            }
        ]
    },

    # 3. IDENTITY, MFA & ACTIVE DIRECTORY
    {
        "doc_id": "ADS-KB-IAM-003",
        "title": "Active Directory Account Lockout, MFA Reset, and Conditional Access",
        "owner": "Identity & Access Management",
        "category": "Identity & Access",
        "products": "Entra ID, Active Directory, Microsoft Authenticator, Conditional Access, BitLocker PIN",
        "platform": "Microsoft Entra ID, Windows 11 Hybrid Joined, iOS/Android Authenticator",
        "sections": [
            {
                "heading": "Resolve recurring Active Directory account lockouts",
                "phrases": '"account locked out every 15 minutes", "AD password lock", "cached credentials locking account"',
                "priority": "P2 High",
                "objective": "Identify stale credential source and unlock user account safely.",
                "intake": "Employee ID; UPN; timestamp of recent password change; list of enrolled mobile devices and RDP sessions.",
                "procedure": [
                    "Verify user identity through approved manager callback or video verification—never ask for passwords or MFA codes.",
                    "Check lockout caller workstation in AD security logs (e.g., stale Windows Credential Manager, mobile mail app, or disconnected RDP session).",
                    "Instruct user to clear saved corporate entries in Windows Credential Manager (`control /name Microsoft.CredentialManager`).",
                    "Sign out of disconnected terminal server sessions and update Wi-Fi 802.1X password on mobile phones.",
                    "Unlock the AD account and monitor for 15 minutes to confirm lockouts cease."
                ],
                "resolve_when": "Stale credential source is purged and account remains unlocked for 30+ minutes.",
                "escalate_when": "Lockouts originate from unknown external IPs (suspected password spray attack).",
                "evidence": "Source workstation name, identity verification method, lockout counter reset.",
                "forbidden": "Disabling account lockout threshold policy; asking user for their current or old password."
            },
            {
                "heading": "Re-register Microsoft Authenticator MFA after phone replacement",
                "phrases": '"new phone MFA broken", "lost authenticator app", "cannot approve sign-in prompt"',
                "priority": "P2 High",
                "objective": "Rebind MFA hardware token after strict out-of-band identity proofing.",
                "intake": "Employee ID; manager confirmation; new mobile device OS version.",
                "procedure": [
                    "Perform mandatory live video identity verification with government/corporate photo ID and manager confirmation.",
                    "Issue a single-use Temporary Access Pass (TAP) valid for 60 minutes via the IAM admin workflow.",
                    "Guide user to `aka.ms/mysecurityinfo` to delete the old phone registration and pair the new Microsoft Authenticator app.",
                    "Verify push notification with number matching works before closing the ticket."
                ],
                "resolve_when": "New Authenticator device is verified and old device registration is removed.",
                "escalate_when": "User fails identity verification or reports unsolicited MFA fatigue push prompts.",
                "evidence": "Manager approval ID, identity verification log, old device removal confirmation.",
                "forbidden": "Issuing a TAP over unverified email/chat; asking user to read out an SMS/MFA one-time code."
            }
        ]
    },

    # 4. MICROSOFT 365 & COLLABORATION
    {
        "doc_id": "ADS-KB-M365-004",
        "title": "Microsoft 365 Outlook OST Corruption, Shared Mailbox, and Teams Sync",
        "owner": "Digital Workplace Engineering",
        "category": "Collaboration & M365",
        "products": "Outlook Desktop, OST cache, Shared Mailbox, Microsoft Teams, OneDrive KFM",
        "platform": "Windows 11, Microsoft 365 Apps for Enterprise",
        "sections": [
            {
                "heading": "Rebuild corrupted Outlook OST cache file",
                "phrases": '"Outlook stuck updating inbox", "cannot open OST file", "emails missing in desktop app"',
                "priority": "P3 Normal",
                "objective": "Rebuild local Exchange Offline Storage Table (.ost) without losing unsynced drafts.",
                "intake": "Asset tag; Outlook build version; current OST file size (`%localappdata%\\Microsoft\\Outlook`); Webmail status.",
                "procedure": [
                    "Confirm emails are visible and up to date in Outlook on the Web (`outlook.office.com`).",
                    "Check if any unsent messages exist in the local Outbox and save drafts to Webmail.",
                    "Close Outlook completely and verify `OUTLOOK.EXE` is not running in Task Manager.",
                    "Navigate to `%localappdata%\\Microsoft\\Outlook` and rename the affected `.ost` file to `.ost.bak`.",
                    "Relaunch Outlook to trigger an automatic clean OST rebuild and set cached Exchange slider to 12 months."
                ],
                "resolve_when": "New OST builds cleanly, folders synchronize, and `.ost.bak` is scheduled for cleanup.",
                "escalate_when": "Issue persists in Outlook Web (Exchange Online mailbox corruption or litigation hold quota full).",
                "evidence": "Old OST size, Webmail check status, post-rebuild sync status.",
                "forbidden": "Deleting `.pst` local archive files without backup; disabling Exchange Online encryption."
            }
        ]
    },

    # 5. ENDPOINT SECURITY, BITLOCKER & EDR
    {
        "doc_id": "ADS-KB-SEC-005",
        "title": "Endpoint BitLocker Recovery, CrowdStrike Quarantine, and Phishing Triage",
        "owner": "Cyber Defense & Endpoint Security",
        "category": "Endpoint Security",
        "products": "BitLocker Drive Encryption, CrowdStrike Falcon EDR, Phishing Triage, USB Block",
        "platform": "Windows 11 Enterprise, Intune MDM, CrowdStrike Falcon Sensor",
        "sections": [
            {
                "heading": "Handle BitLocker recovery screen after BIOS/firmware update",
                "phrases": '"blue screen asking for 48-digit BitLocker key", "BitLocker recovery after reboot"',
                "priority": "P2 High",
                "objective": "Guide user to self-service recovery portal or verify TPM PCR binding safely.",
                "intake": "Asset tag; first 8 digits of Key ID shown on screen; reason for prompt (BIOS update, dock change).",
                "procedure": [
                    "Instruct user to unplug external USB drives or thunderbolt docks and reboot once to see if TPM unseals automatically.",
                    "If prompt remains, direct user from their mobile device to the corporate self-service portal (`myaccount.microsoft.com`) to view their device's recovery key.",
                    "Never paste raw 48-digit BitLocker recovery keys into chat logs or unencrypted tickets.",
                    "Once booted into Windows, run `manage-bde -protectors -enable C:` to re-seal the TPM 2.0 PCR registers."
                ],
                "resolve_when": "Device boots into Windows and TPM protector is re-sealed across reboot.",
                "escalate_when": "Key ID does not match Entra ID/Intune escrow; SSD reports SMART hardware failure.",
                "evidence": "8-digit Key ID prefix, trigger cause (firmware/dock), TPM re-seal confirmation.",
                "forbidden": "Pasting the 48-digit recovery key in plain-text chat; permanently decrypting the OS drive."
            },
            {
                "heading": "Triage CrowdStrike Falcon network containment or quarantine alert",
                "phrases": '"CrowdStrike blocked my file", "laptop isolated from network by security", "EDR quarantine"',
                "priority": "P1/P2 Security incident",
                "objective": "Preserve forensic state and route containment review to SOC.",
                "intake": "Asset tag; detection ID; file path or process name; activity immediately prior to alert.",
                "procedure": [
                    "Instruct the user NOT to power off or reboot the laptop so volatile memory forensics remain intact.",
                    "Record the file path, hash, or script activity the user was running when the alert triggered.",
                    "Create a P1/P2 Security Incident ticket and route directly to the SOC Queue.",
                    "Wait for explicit SOC clearance before lifting network containment or whitelisting a false positive."
                ],
                "resolve_when": "SOC completes triage and either clears the host or initiates incident re-imaging.",
                "escalate_when": "Always escalate EDR detections to SOC; never attempt to stop or uninstall the Falcon sensor.",
                "evidence": "Detection ID, hostname, user statement, SOC ticket reference.",
                "forbidden": "Attempting to disable/uninstall CrowdStrike Falcon; instructing user to wipe evidence."
            }
        ]
    }
]

if __name__ == "__main__":
    for article in KB_ARTICLES:
        build_kb_pdf(article)