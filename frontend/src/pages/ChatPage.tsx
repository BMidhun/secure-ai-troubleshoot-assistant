// src/pages/ChatPage.tsx
import React, { useState, useRef, useEffect } from "react";
import {
  Box,
  Paper,
  IconButton,
  Typography,
  CircularProgress,
  Chip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Avatar,
  InputBase,
  Grid,
  Card,
  CardActionArea,
  Divider,
} from "@mui/material";
import SendRoundedIcon from "@mui/icons-material/SendRounded";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import VerifiedUserRoundedIcon from "@mui/icons-material/VerifiedUserRounded";
import SecurityRoundedIcon from "@mui/icons-material/SecurityRounded";
import MenuBookRoundedIcon from "@mui/icons-material/MenuBookRounded";
import SmartToyRoundedIcon from "@mui/icons-material/SmartToyRounded";
import PersonOutlineRoundedIcon from "@mui/icons-material/PersonOutlineRounded";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";

interface Message {
  role: "user" | "assistant";
  text: string;
  status?: string;
  branches?: string[];
  verified?: boolean;
  blocked?: boolean;
}

const QUICK_PROMPTS = [
  { title: "VPN Connectivity", query: "Getting VPN Connectivity issue." },
  {
    title: "Asset Allocation",
    query: "I need a second laptop for a segregated client project.",
  },
  {
    title: "Identity & Access",
    query: "My Active Directory account keeps locking out.",
  },
  {
    title: "Hardware Safety",
    query: "There is smoke and a burning smell coming from my USB port.",
  },
];

export default function ChatPage() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (customQuery?: string) => {
    const queryText = customQuery || input;
    if (!queryText.trim()) return;

    const userMsg: Message = { role: "user", text: queryText };
    setMessages((prev) => [
      ...prev,
      userMsg,
      {
        role: "assistant",
        text: "",
        status: "Analyzing request and structuring plan...",
        branches: [],
        verified: false,
      },
    ]);
    if (!customQuery) setInput("");
    setLoading(true);

    try {
      const response = await fetch("http://localhost:8000/api/stream-chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream",
        },
        body: JSON.stringify({ user_id: "emp-104", message: queryText }),
      });

      if (!response.body) throw new Error("No response body");
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split("\n\n");
        buffer = events.pop() || "";

        for (const evt of events) {
          const trimmed = evt.trim();
          if (!trimmed.startsWith("data: ")) continue;

          try {
            const data = JSON.parse(trimmed.slice(6));

            setMessages((prev) => {
              if (prev.length === 0) return prev;
              const updated = [...prev];
              const lastIdx = updated.length - 1;
              const currentLast = { ...updated[lastIdx] };

              if (data.type === "branches") {
                currentLast.branches = data.branches;
                currentLast.status =
                  "Searching runbooks and executing diagnostics...";
              } else if (data.type === "status") {
                currentLast.status = data.status;
              } else if (data.type === "token") {
                currentLast.status = undefined;
                currentLast.text = (currentLast.text || "") + data.content;
              } else if (data.type === "reset_draft") {
                currentLast.text = "";
                currentLast.status =
                  "Refining solution based on policy guidelines...";
              } else if (data.type === "critique") {
                currentLast.verified = data.verified;
                currentLast.status = undefined;
              } else if (data.type === "error") {
                currentLast.text = data.reply;
                currentLast.blocked = true;
                currentLast.status = undefined;
              } else if (data.type === "done") {
                currentLast.status = undefined;
              }

              updated[lastIdx] = currentLast;
              return updated;
            });
          } catch (parseErr) {
            console.warn("Skipped malformed SSE packet:", parseErr);
          }
        }
      }
    } catch {
      setMessages((prev) => {
        const updated = [...prev];
        const lastIdx = updated.length - 1;
        updated[lastIdx] = {
          ...updated[lastIdx],
          text: "Error connecting to the Secure AI backend service. Please try again later.",
          blocked: true,
          status: undefined,
        };
        return updated;
      });
    } finally {
      setLoading(false);
    }
  };

  const renderFormattedText = (text: string) => {
    // Splits text by exact pattern:
    const parts = text.split(/(\]+\])/g);
    return parts.map((part, index) => {
      if (part.startsWith("[Source:")) {
        // Extract just the filename (e.g., "ADS-KB-ASSET-001.pdf")
        const sourceName = part
          .replace(/\[Source:\s*/, "")
          .replace("]", "")
          .trim();
        const documentUrl = `http://localhost:8000/api/documents/${sourceName}`;

        return (
          <Chip
            key={index}
            icon={<MenuBookRoundedIcon sx={{ fontSize: "14px !important" }} />}
            label={sourceName}
            size="small"
            onClick={() => window.open(documentUrl, "_blank")}
            sx={{
              mx: 0.5,
              my: 0.2,
              fontWeight: 600,
              fontSize: "0.70rem",
              bgcolor: "#e2e8f0",
              color: "#0f766e",
              cursor: "pointer",
              transition: "all 0.2s ease",
              "&:hover": {
                bgcolor: "#ccfbf1",
                transform: "translateY(-1px)",
                boxShadow: "0 2px 6px rgba(15, 118, 110, 0.2)",
              },
            }}
          />
        );
      }
      return <span key={index}>{part}</span>;
    });
  };

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        height: "calc(100vh - 64px)",
        bgcolor: "#f8fafc",
      }}
    >
      {/* Scrollable Chat Area */}
      <Box sx={{ flex: 1, overflowY: "auto", px: { xs: 2, md: 4 }, py: 4 }}>
        <Box
          sx={{
            maxWidth: 860,
            mx: "auto",
            display: "flex",
            flexDirection: "column",
            gap: 4,
          }}
        >
          {/* Empty State Welcome Dashboard */}
          {messages.length === 0 && (
            <Box
              sx={{
                mt: 4,
                mb: 8,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                animation: "fadeIn 0.5s ease-in",
              }}
            >
              <Avatar
                sx={{
                  width: 64,
                  height: 64,
                  bgcolor: "#0f766e",
                  mb: 2,
                  boxShadow: "0 4px 12px rgba(15, 118, 110, 0.2)",
                }}
              >
                <AutoAwesomeIcon fontSize="large" />
              </Avatar>
              <Typography
                variant="h5"
                sx={{ fontWeight: 700, color: "#1e293b", mb: 1 }}
              >
                How can I assist you today?
              </Typography>
              <Typography
                variant="body1"
                sx={{
                  color: "#64748b",
                  mb: 4,
                  textAlign: "left",
                  maxWidth: 500,
                }}
              >
                I am your Secure AI IT Assistant. I can help troubleshoot VPN
                issues, manage asset requests, and answer security policy
                questions securely.
              </Typography>

              <Grid container spacing={2} sx={{ maxWidth: 700 }}>
                {QUICK_PROMPTS.map((item, idx) => (
                  <Grid size={{ xs: 12, sm: 6 }} key={idx}>
                    <Card
                      variant="outlined"
                      sx={{
                        borderRadius: 3,
                        borderColor: "#e2e8f0",
                        transition: "0.2s",
                        "&:hover": {
                          borderColor: "#0f766e",
                          boxShadow: "0 4px 12px rgba(0,0,0,0.05)",
                        },
                      }}
                    >
                      <CardActionArea
                        onClick={() => handleSend(item.query)}
                        disabled={loading}
                        sx={{ p: 2, height: "100%" }}
                      >
                        <Typography
                          variant="subtitle2"
                          sx={{ fontWeight: 700, color: "#0f766e", mb: 0.5 }}
                        >
                          {item.title}
                        </Typography>
                        <Typography variant="body2" sx={{ color: "#475569" }}>
                          "{item.query}"
                        </Typography>
                      </CardActionArea>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            </Box>
          )}

          {/* Render Messages */}
          {messages.map((m, i) => {
            const isUser = m.role === "user";
            return (
              <Box
                key={i}
                sx={{
                  display: "flex",
                  flexDirection: isUser ? "row-reverse" : "row",
                  gap: 2,
                  alignItems: "flex-start",
                }}
              >
                <Avatar
                  sx={{
                    bgcolor: isUser ? "#cbd5e1" : "#163a5f",
                    width: 36,
                    height: 36,
                  }}
                >
                  {isUser ? (
                    <PersonOutlineRoundedIcon sx={{ color: "#475569" }} />
                  ) : (
                    <SmartToyRoundedIcon sx={{ color: "#fff" }} />
                  )}
                </Avatar>

                <Box
                  sx={{
                    maxWidth: "75%",
                    display: "flex",
                    flexDirection: "column",
                    alignItems: isUser ? "flex-end" : "flex-start",
                  }}
                >
                  {/* AI Metadata Badges (Verified / Blocked) */}
                  {!isUser && (m.verified || m.blocked) && (
                    <Box sx={{ display: "flex", gap: 1, mb: 1 }}>
                      {m.verified && (
                        <Chip
                          icon={
                            <VerifiedUserRoundedIcon
                              sx={{ fontSize: "14px !important" }}
                            />
                          }
                          label="Consensus Verified"
                          size="small"
                          color="success"
                          variant="outlined"
                          sx={{
                            height: 22,
                            fontSize: "0.7rem",
                            fontWeight: 600,
                            bgcolor: "#f0fdf4",
                          }}
                        />
                      )}
                      {m.blocked && (
                        <Chip
                          icon={
                            <SecurityRoundedIcon
                              sx={{ fontSize: "14px !important" }}
                            />
                          }
                          label="Policy Intervention"
                          size="small"
                          color="error"
                          variant="outlined"
                          sx={{
                            height: 22,
                            fontSize: "0.7rem",
                            fontWeight: 600,
                            bgcolor: "#fef2f2",
                          }}
                        />
                      )}
                    </Box>
                  )}

                  {/* Message Bubble */}
                  <Paper
                    elevation={isUser ? 0 : 1}
                    sx={{
                      p: 2.5,
                      bgcolor: isUser ? "#0f766e" : "#ffffff",
                      color: isUser ? "#ffffff" : "#1e293b",
                      borderRadius: isUser
                        ? "16px 4px 16px 16px"
                        : "4px 16px 16px 16px",
                      border: isUser ? "none" : "1px solid #e2e8f0",
                      boxShadow: isUser ? "none" : "0 2px 8px rgba(0,0,0,0.04)",
                    }}
                  >
                    {/* Live Agent Status */}
                    {m.status && (
                      <Box
                        sx={{
                          display: "flex",
                          alignItems: "flex-start",
                          gap: 1.5,
                          mb: m.text ? 2 : 0,
                          color: "#0f766e",
                        }}
                      >
                        <CircularProgress
                          size={16}
                          thickness={5}
                          sx={{ color: "#0f766e" }}
                        />
                        <Typography
                          variant="body2"
                          sx={{ fontWeight: 600, fontStyle: "italic" }}
                        >
                          {m.status}
                        </Typography>
                      </Box>
                    )}

                    {/* Main Text Content */}
                    {m.text && (
                      <Typography
                        variant="body1"
                        sx={{
                          whiteSpace: "pre-wrap",
                          lineHeight: 1.6,
                          fontSize: "0.95rem",
                          textAlign: "left",
                        }}
                      >
                        {renderFormattedText(m.text)}
                      </Typography>
                    )}

                    {/* LangGraph Reasoning Branches Accordion */}
                    {m.branches && m.branches.length > 0 && (
                      <Accordion
                        elevation={0}
                        sx={{
                          mt: 2,
                          bgcolor: "#f1f5f9",
                          borderRadius: "8px !important",
                          "&:before": { display: "none" },
                        }}
                      >
                        <AccordionSummary
                          expandIcon={<ExpandMoreIcon />}
                          sx={{
                            minHeight: "40px !important",
                            ".MuiAccordionSummary-content": {
                              my: "10px !important",
                            },
                          }}
                        >
                          <Typography
                            variant="subtitle2"
                            sx={{
                              fontWeight: 600,
                              color: "#475569",
                              fontSize: "0.8rem",
                            }}
                          >
                            View Diagnostic Plan ({m.branches.length} paths)
                          </Typography>
                        </AccordionSummary>
                        <AccordionDetails sx={{ pt: 0, pb: 2, px: 2 }}>
                          <Divider sx={{ mb: 1.5, borderColor: "#cbd5e1" }} />
                          <Box
                            component="ul"
                            sx={{
                              m: 0,
                              pl: 2,
                              typography: "body2",
                              color: "#475569",
                              fontSize: "0.85rem",
                            }}
                          >
                            {m.branches.map((b, idx) => (
                              <li key={idx} style={{ marginBottom: 6 }}>
                                {b}
                              </li>
                            ))}
                          </Box>
                        </AccordionDetails>
                      </Accordion>
                    )}
                  </Paper>
                </Box>
              </Box>
            );
          })}
          <div ref={messagesEndRef} />
        </Box>
      </Box>

      {/* Sticky Input Footer */}
      <Box sx={{ bgcolor: "transparent", pt: 2, pb: 4, px: { xs: 2, md: 4 } }}>
        <Box sx={{ maxWidth: 860, mx: "auto" }}>
          <Paper
            elevation={3}
            sx={{
              display: "flex",
              alignItems: "flex-end",
              p: "8px 12px",
              borderRadius: 4,
              bgcolor: "#ffffff",
              border: "1px solid #cbd5e1",
              boxShadow: "0 10px 25px rgba(0,0,0,0.05)",
            }}
          >
            <InputBase
              fullWidth
              multiline
              maxRows={4}
              placeholder="Message Secure AI Assistant..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  if (!loading) handleSend();
                }
              }}
              disabled={loading}
              sx={{ ml: 1, py: 1, fontSize: "0.95rem", color: "#1e293b" }}
            />
            <Box sx={{ mb: 0.5, ml: 1 }}>
              <IconButton
                color="primary"
                onClick={() => handleSend()}
                disabled={loading || !input.trim()}
                sx={{
                  bgcolor: input.trim() && !loading ? "#0f766e" : "#e2e8f0",
                  color: input.trim() && !loading ? "#fff" : "#94a3b8",
                  transition: "0.2s",
                  "&:hover": { bgcolor: "#115e59" },
                }}
              >
                {loading ? (
                  <CircularProgress size={20} color="inherit" />
                ) : (
                  <SendRoundedIcon fontSize="small" />
                )}
              </IconButton>
            </Box>
          </Paper>
          <Typography
            variant="caption"
            sx={{
              display: "block",
              textAlign: "center",
              mt: 1.5,
              color: "#94a3b8",
            }}
          >
            AI-generated content may be inaccurate. Actions requiring escalation
            will automatically log an IT ticket.
          </Typography>
        </Box>
      </Box>
    </Box>
  );
}
