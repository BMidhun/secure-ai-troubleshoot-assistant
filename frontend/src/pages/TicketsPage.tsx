import { useEffect, useState } from "react";
import {
  Box,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Button,
} from "@mui/material";
import RefreshIcon from "@mui/icons-material/Refresh";
import AssignmentIcon from "@mui/icons-material/Assignment";

interface Ticket {
  ticket_id: string;
  user_id: string;
  summary: string;
  severity: string;
  status: string;
  created_at: string;
}

export default function TicketsPage() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchTickets = async () => {
    setLoading(true);
    try {
      const res = await fetch("http://localhost:8000/api/tickets");
      const data = await res.json();
      setTickets(data);
    } catch (err) {
      console.error("Failed to fetch tickets", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const getInitialTickets = async () => fetchTickets();

    getInitialTickets();
  }, []);

  const getSeverityColor = (sev: string) => {
    switch (sev) {
      case "P1":
        return "error";
      case "P2":
        return "warning";
      case "P3":
        return "info";
      default:
        return "default";
    }
  };

  return (
    <Box sx={{ maxWidth: 1000, mx: "auto", p: 3 }}>
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          mb: 3,
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
          <AssignmentIcon color="primary" sx={{ fontSize: 32 }} />
          <div>
            <Typography variant="h5" sx={{ fontWeight: 600, color: "#1e293b" }}>
              ServiceNow Incident Logs
            </Typography>
          </div>
        </Box>
        <Button
          variant="text"
          startIcon={<RefreshIcon />}
          onClick={fetchTickets}
          disabled={loading}
        ></Button>
      </Box>

      <TableContainer component={Paper} elevation={1} sx={{ borderRadius: 2 }}>
        <Table>
          <TableHead sx={{ bgcolor: "#f1f5f9" }}>
            <TableRow>
              <TableCell sx={{ fontWeight: 600 }}>Ticket ID</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Severity</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>User ID</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Summary</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Status</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Created At</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {tickets.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={6}
                  align="center"
                  sx={{ py: 4, color: "text.secondary" }}
                >
                  No tickets logged yet. Trigger ticket creation from the AI
                  Troubleshooter chat!
                </TableCell>
              </TableRow>
            ) : (
              tickets.map((t) => (
                <TableRow key={t.ticket_id} hover>
                  <TableCell sx={{ fontWeight: 600, color: "#0f766e" }}>
                    {t.ticket_id}
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={t.severity}
                      size="small"
                      color={getSeverityColor(t.severity)}
                      sx={{ fontWeight: 600 }}
                    />
                  </TableCell>
                  <TableCell>{t.user_id}</TableCell>
                  <TableCell>{t.summary}</TableCell>
                  <TableCell>
                    <Chip
                      label={t.status}
                      size="small"
                      variant="outlined"
                      color="success"
                    />
                  </TableCell>
                  <TableCell
                    sx={{ color: "text.secondary", fontSize: "0.85rem" }}
                  >
                    {new Date(t.created_at).toLocaleString()}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}
