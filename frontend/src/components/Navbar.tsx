import { AppBar, Toolbar, Typography, Button, Box } from "@mui/material";
import { useNavigate, useLocation } from "react-router";
import ChatIcon from "@mui/icons-material/Chat";
import AssignmentIcon from "@mui/icons-material/Assignment";
import SecurityIcon from "@mui/icons-material/Security";

export default function Navbar() {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <AppBar position="static" elevation={1} sx={{ bgcolor: "#163a5f" }}>
      <Toolbar sx={{ justifyContent: "space-between" }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
          <SecurityIcon sx={{ color: "#2dd4bf" }} />
          <Typography
            variant="h6"
            component="div"
            sx={{ fontWeight: 600, letterSpacing: 0.5 }}
          >
            Secure AI IT Support Assistant
          </Typography>
        </Box>
        <Box sx={{ display: "flex", gap: 1 }}>
          <Button
            color="inherit"
            startIcon={<ChatIcon />}
            onClick={() => navigate("/chat")}
            sx={{
              bgcolor:
                location.pathname === "/chat"
                  ? "rgba(255,255,255,0.12)"
                  : "transparent",
              fontWeight: location.pathname === "/chat" ? 600 : 400,
            }}
          >
            AI Troubleshooter
          </Button>
          <Button
            color="inherit"
            startIcon={<AssignmentIcon />}
            onClick={() => navigate("/tickets")}
            sx={{
              bgcolor:
                location.pathname === "/tickets"
                  ? "rgba(255,255,255,0.12)"
                  : "transparent",
              fontWeight: location.pathname === "/tickets" ? 600 : 400,
            }}
          >
            Support Tickets
          </Button>
        </Box>
      </Toolbar>
    </AppBar>
  );
}
