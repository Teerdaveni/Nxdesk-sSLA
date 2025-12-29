// --- WebSocket-based Chat Implementation ---


import { useEffect, useState, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useSelector } from "react-redux";
import { ToastContainer, toast } from "react-toastify";
import { formatDate } from "../../utils/formatDate";
import "react-toastify/dist/ReactToastify.css";
import { ChevronLeft, X, Paperclip, Trash2, Clock } from "lucide-react";
import Sidebar from "../../components/Sidebar";
import ChatbotPopup from "../../components/ChatBot";
import QuillTextEditor from "../CreateIssue/Components/QuillTextEditor";
import { axiosInstance } from "../../utils/axiosInstance";
import ResolutionInfo from "../ResolutionInfo";
import ChatUI from "./ChatUI";
import QuestionToUserModal from "./components/QuestionToUserModal";
import AssignmentModal from "./components/AssignmentModal";
import PriorityModal from "./components/PriorityModal";
import CloseTicketModal from "./components/CloseTicketModal";

import {
  Building2,
  Settings,
  User,
  Users,
  UserCheck,
  Headphones,
  FileText,
  MessageSquare,
  AlertTriangle,
  Flag,
  FolderOpen,
  UserCog,
  Hash,
  Globe,
  Wrench,
  Calendar,
  Target,
  Briefcase,
  Mail,
  Link,
} from "lucide-react";

export default function ResolveIssue() {
  const [timeRemaining, setTimeRemaining] = useState({
    hours: 0,
    minutes: 0,
    seconds: 0,
  });
  const [isExpried, setIsExpired] = useState(false);
  const { ticketId } = useParams();
  const navigate = useNavigate();
  const userProfile = useSelector((state) => state.userProfile.user);

  const [ticket, setTicket] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [editableStatus, setEditableStatus] = useState("");
  const [statusChoices, setStatusChoices] = useState([]);
  const [impactChoices, setImpactChoices] = useState([]);
  const [priorityChoices, setPriorityChoices] = useState([]);
  const [supportTeamChoices, setSupportTeamChoices] = useState([]);
  const [attachments, setAttachments] = useState([]);
  const [expandEditor, setExpandEditor] = useState(false);
  const [assignmentData, setAssignmentData] = useState({
    assigneeId: "",
    assignee: "",
    supportOrgId: "",
    solutionGroupId: "",
  });
  const [currentTab, setCurrentTab] = useState("Notes");
  const [questionData, setQuestionData] = useState({
    ticket: "",
    comment: "",
    commentHTML: "",
    attachments: [],
  });
  const [isQuestionModalOpen, setIsQuestionModalOpen] = useState(false);
  const [isAssignmentModalOpen, setIsAssignmentModalOpen] = useState(false);
  const [isPriorityModalOpen, setIsPriorityModalOpen] = useState(false);
  const [isCloseModalOpen, setIsCloseModalOpen] = useState(false);
  // History state
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  // --- Pure WebSocket Chat Implementation ---
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState("");
  const chatWsRef = useRef(null);
  const currentUserId = userProfile?.employee_id;

  useEffect(() => {
    if (!ticketId) return;
    const accessToken = localStorage.getItem("access_token");
    const ws = new window.WebSocket(`ws://127.0.0.1:8000/ws/ticket/${ticketId}/?token=${accessToken}`);
    // const ws = new window.WebSocket(`ws://192.168.0.230:8080/ws/ticket/${ticketId}/?token=${accessToken}`);
    chatWsRef.current = ws;

    ws.onopen = () => {
      console.log("Connected to chat");
      console.log("WebSocket Instance:", ws);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("WS Message:", data);
        // Handle backend format: {type: 'chat_message', message, username, created_at}
        if (data.type === "chat_message") {
          setChatMessages((prev) => [
            ...prev,
            {
              message: data.message,
              user: { username: data.username },
              created_at: data.created_at,
            },
          ]);
        } else if (data.action === "chat_init" && Array.isArray(data.messages)) {
          setChatMessages(data.messages);
        } else if (data.action === "error") {
          console.error("Chat error:", data.message);
          toast.error(data.message);
        }
      } catch (err) {
        console.error("Chat WebSocket message error:", err);
      }
    };



    ws.onerror = (err) => {
      console.error("Chat WebSocket error:", err);
    };

    ws.onclose = () => {
      console.log("Chat socket closed");
    };

    return () => {
      if (chatWsRef.current) chatWsRef.current.close();
    };
  }, [ticketId]);

  const sendChatMessage = () => {
    console.log("Sending message:", chatInput);
    console.log("WebSocket readyState:", chatWsRef.current.readyState);
    console.log("Current User ID:", currentUserId);
    console.log("WebSocket instance:", chatWsRef.current);

    if (!chatInput.trim() || !chatWsRef.current || !currentUserId) return;

    if (chatWsRef.current.readyState !== 1) {
      toast.error("Chat connection not open. Please wait or refresh.");
      return;
    }
    try {


      chatWsRef.current.send(
        JSON.stringify({
          action: "send_message",
          message: chatInput,
          user_id: currentUserId,
        })
      );
      setChatInput("");
    } catch (err) {
      toast.error("Failed to send message.");
      console.error("Send error:", err);
    }
  };



  const getFieldIcon = (label) => {
    const iconMap = {
      Number: Hash,
      "Service Domain": Building2,
      "Service Type": Settings,
      Requestor: User,
      "Solution Group": Users,
      Assignee: UserCheck,
      Status: Flag,
      Impact: AlertTriangle,
      Priority: Target,
      Project: Briefcase,
      Product: Building2,
      "Created On": Calendar,
      "Updated On": Calendar,
      "Reference Ticket": Link,
      "Contact Number": Headphones,
      Description: FileText,
    };

    return iconMap[label] || FileText; // Default icon if not found
  };

  // Reference to ChatUI component - will be used to access its methods
  const chatUIRef = useRef(null);

  // Refs for content scrolling
  const mainContentRef = useRef(null);
  const tabContentRef = useRef(null);

  // Initialize editable status when ticket data is loaded
  useEffect(() => {
    if (ticket) {
      setEditableStatus(ticket.status || "Open");
    }
  }, [ticket]);


  // --- WebSocket-based SLA Timer Implementation ---
  const [slaStatus, setSlaStatus] = useState("");
  const [remainingSeconds, setRemainingSeconds] = useState(0);
  const [slaExpired, setSlaExpired] = useState(false);
  const wsRef = useRef(null);
  const intervalRef = useRef(null);

  // Format seconds to HH:MM:SS
  const formatSLA = (secs) => {
    const h = Math.floor(secs / 3600);
    const m = Math.floor((secs % 3600) / 60);
    const s = secs % 60;
    return `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  // Move startSLATimer and stopSLATimer outside of useEffect
  function startSLATimer() {
    if (intervalRef.current) return; // Prevent multiple intervals
    intervalRef.current = setInterval(() => {
      setRemainingSeconds((prev) => {
        if (prev <= 1) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
          setSlaExpired(true);
          setSlaStatus("Expired");
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  }

  function stopSLATimer() {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }

  useEffect(() => {
    const accessToken = localStorage.getItem("access_token");
    // Connect to Django Channels WebSocket
    const ws = new window.WebSocket(`ws://127.0.0.1:8000/ws/timer/${ticketId}/?token=${accessToken}`);
    // const ws = new window.WebSocket(`ws://192.168.0.230:8080/ws/timer/${ticketId}/?token=${accessToken}`);
    wsRef.current = ws;


    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("WebSocket Data:", data);

        if (data.action === "timer_init" || data.action === "status_update" || data.action === "timer_update") {
          setSlaStatus(data.sla_status);

          // Parse "HH:MM:SS.ssssss" to seconds
          const [h, m, s] = (data.remaining_time || "0:0:0").split(":");
          const [sec] = (s || "0").split(".");
          const totalSeconds = (parseInt(h) || 0) * 3600 + (parseInt(m) || 0) * 60 + (parseInt(sec) || 0);

          console.log(`Setting remainingSeconds to: ${totalSeconds}, SLA Status: ${data.sla_status}`);
          setRemainingSeconds(totalSeconds > 0 ? totalSeconds : 0);
          setSlaExpired(totalSeconds <= 0);

          if (data.sla_status === "Paused") {
            console.log("Pausing SLA timer");
            stopSLATimer();
          } else if (data.sla_status === "Stopped") {
            console.log("SLA timer stopped");
            stopSLATimer();
          } else if (data.sla_status === "Scheduled") {
            console.log("SLA timer scheduled");
            stopSLATimer();
          } else if (data.sla_status === "Running" || data.sla_status === "Active") {
            console.log("Starting SLA timer");
            stopSLATimer(); // Stop any existing timer first
            startSLATimer();
          } else if (data.sla_status === "Expired") {
            console.log("SLA timer expired");
            stopSLATimer();
            setSlaExpired(true);
          }
        }
      } catch (err) {
        console.error("WebSocket message error:", err);
      }
    }; ws.onerror = (err) => {
      console.error("WebSocket error:", err);
    };

    ws.onclose = () => {
      stopSLATimer();
    };

    // Cleanup on unmount
    return () => {
      if (wsRef.current) wsRef.current.close();
      stopSLATimer();
    };
  }, [ticketId]);

  const formatTime = (time) => time.toString().padStart(2, "0");
  // Fetch ticket details
  const fetchTicketDetails = async () => {
    try {
      const response = await axiosInstance.get(`ticket/tickets/${ticketId}/`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
        },
      });
      console.log("Ticket Details", response);
      setTicket(response.data);
      setAttachments(response.data.attachments || []);
      setQuestionData((prev) => ({
        ...prev,
        ticket: response.data.ticket_id,
      }));

      // Initialize assignment data
      setAssignmentData({
        assigneeId: "",
        assignee: response.data.assignee || "",
        supportOrgId: response.data.developer_organization || "",
        solutionGroupId: response.data.solution_grp || "",
      });
    } catch (error) {
      console.error("Error fetching ticket details:", error);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    fetchTicketDetails();
  }, [ticketId]);

  // useEffect(() => {
  //   fetchSLADetails();
  // }, []);
  // Fetch ticket choices for dropdowns
  useEffect(() => {
    const fetchTicketChoices = async () => {
      try {
        const response = await axiosInstance.get(`ticket/ticket/choices/`, {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("access_token")}`,
          },
        });
        console.log("All choices", response);
        setPriorityChoices(response.data.priority_choices || []);
        setImpactChoices(response.data.impact_choices || []);
        setStatusChoices(response.data.status_choices || []);
        setSupportTeamChoices(response.data.support_team_choices || []);
      } catch (error) {
        console.error("Error fetching ticket choices:", error);
      }
    };

    fetchTicketChoices();
  }, []);

  // Fetch history when History tab is selected
  useEffect(() => {
    if (currentTab === "History" && ticket?.ticket_id) {
      fetchHistory();
    }
  }, [currentTab, ticket?.ticket_id]);

  useEffect(() => {
    if (tabContentRef.current) {
      // Ensure the tab content is visible
      tabContentRef.current.scrollIntoView({
        behavior: "smooth",
        block: "nearest",
      });
    }
  }, [currentTab]);

  // Fetch history function
  const fetchHistory = async () => {
    setHistoryLoading(true);
    try {
      const response = await axiosInstance.get(
        `ticket/history/?ticket=${ticket?.ticket_id}`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("access_token")}`,
          },
        }
      );
      const sortedHistory = (response.data || []).sort(
        (a, b) =>
          new Date(b.modified_at || b.created_at) -
          new Date(a.modified_at || a.created_at)
      );
      setHistory(sortedHistory);
    } catch (error) {
      console.error("Error fetching history:", error);
      toast.error("Failed to fetch ticket history");
    } finally {
      setHistoryLoading(false);
    }
  };

  // Add history entry function
  const addHistoryEntry = async (title, ticketId) => {
    try {
      await axiosInstance.post(
        "ticket/history/",
        {
          title: title,
          ticket: ticketId,
        },
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("access_token")}`,
          },
        }
      );
      // Refresh history if History tab is active
      if (currentTab === "History") {
        fetchHistory();
      }
    } catch (error) {
      console.error("Error adding history entry:", error);
    }
  };

  const toggleSidebar = () => setIsSidebarOpen(!isSidebarOpen);


  const handleQuestionToUser = async () => {
    setIsQuestionModalOpen(true);

    // Only run if SLA update succeeded
  };


  const handleAssignClick = () => {
    setIsAssignmentModalOpen(true);
  };

  const handleChangePriority = () => {
    setIsPriorityModalOpen(true);
  };

  const handleCloseTicket = () => {
    setIsCloseModalOpen(true);
  };

  const handleConfirmClose = (reason) => {
    setNewStatus("Resolved");
    setIsCloseModalOpen(false);
    setTimeout(() => {
      const entry = `Reason: ${reason} - <span style="color: red;">Ticket closed</span>`;
      addHistoryEntry(entry, ticket?.ticket_id);
    }, 3000);
  };

  const handleAssignmentSuccess = (updatedTicket) => {
    // Update the ticket state with the new assignment data
    setTicket(updatedTicket);
    setAssignmentData({
      assigneeId: "",
      assignee: updatedTicket.assignee || "",
      supportOrgId: updatedTicket.developer_organization || "",
      solutionGroupId: updatedTicket.solution_grp || "",
    });
    addHistoryEntry(
      `Ticket assigned to ${updatedTicket.assignee}`,
      updatedTicket.ticket_id
    );
  };

  const handlePriorityUpdate = (updatedTicket) => {
    // Update the ticket state with the new priority data
    setTicket(updatedTicket);

    // Add history entry
    addHistoryEntry(
      `Priority changed to ${updatedTicket.priority}`,
      updatedTicket.ticket_id
    );
  };

  const refetchTicketDetails = () => {
    fetchTicketDetails();
  };

  const updateTicketStatus = (newStatus) => {
    const oldStatus = ticket?.status;
    setTicket((prev) => ({ ...prev, status: newStatus }));
    setEditableStatus(newStatus);

    // Add history entry
    if (oldStatus !== newStatus) {
      addHistoryEntry(
        `Status changed from ${oldStatus} to ${newStatus}`,
        ticket?.ticket_id
      );
    }
  };

  // Helper function to get impact code from label
  const getImpactCode = (impactLabel) => {
    if (!impactLabel || !impactChoices.length) return null;

    const impactItem = impactChoices.find((item) => item[1] === impactLabel);
    return impactItem ? impactItem[0] : null;
  };

  // Helper function to get priority ID from label
  const getPriorityId = (priorityLabel) => {
    if (!priorityLabel || !priorityChoices.length) return null;

    const priorityItem = priorityChoices.find(
      (item) => item.urgency_name === priorityLabel
    );
    return priorityItem ? priorityItem.priority_id : null;
  };

  const setNewStatus = async (status) => {
    try {
      const response = await axiosInstance.put(
        `ticket/tickets/${ticketId}/`,
        {
          status: status,
        },
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("access_token")}`,
          },
        }
      );
      setTicket(response.data);
      setEditableStatus(status);
      toast.success(`Status updated to ${status}!`);
      return true
    } catch (error) {
      console.error("Failed to update status:", error);
      toast.error("Failed to update ticket status");
      return false;
    }
  };

  // Handle Start Work button click
  const handleStartWork = async () => {
    const success = await setNewStatus("Working in Progress");

    if (!success) {
      console.warn("Status update failed, stopping workflow.");
      return; // stop further execution
    }

    console.log("Status updated successfully.");
    // continue only if success === true
    setSlaStatus("Active");
    startSLATimer();
    addHistoryEntry("Work started on ticket", ticket?.ticket_id);
  };


  // Function to handle chat updates and add to history
  const handleChatUpdate = (message, messageType = "comment") => {
    // Add history entry for chat updates
    let historyTitle = "";

    switch (messageType) {
      case "question":
        historyTitle = "Question sent to user";
        break;
      case "reply":
        historyTitle = "Reply added to ticket";
        break;
      case "note":
        historyTitle = "Internal note added";
        break;
      default:
        historyTitle = "Comment added to ticket";
    }

    addHistoryEntry(historyTitle, ticket?.ticket_id);
  };

  // SLA timer refresh helper
  // const refreshSlaTimer = () => {
  //   fetchSLADetails();
  // };

  // Generate tabs array dynamically
  const generateTabs = () => {
    const baseTabs = ["Notes", "RelatedRecords", "History"];

    // Case 1: If the ticket status is "Resolved", always include "ResolutionInfo"
    if (ticket?.status === "Resolved") {
      baseTabs.push("ResolutionInfo");
    }
    // Case 2: If the status is NOT "Resolved", only include "ResolutionInfo" if the logged-in user is the assignee
    else if (
      ticket?.assignee?.toLowerCase() === userProfile?.username?.toLowerCase()
    ) {
      baseTabs.push("ResolutionInfo");
    }

    return baseTabs;
  };

  const tabs = generateTabs();

  const renderField = (label, value, additionalClasses = "") => {
    const displayValue = value || "N/A";
    const fieldClasses = `bg-gray-50 border px-2 py-1 cursor-not-allowed outline-none text-sm w-[50%] ${!value ? "italic text-gray-400" : ""
      } ${additionalClasses}`;

    const IconComponent = getFieldIcon(label);

    return (
      <div className="flex justify-start items-center mb-2">
        <div className="flex items-center text-gray-600 text-base w-[25%]">
          <IconComponent
            size={16}
            className="mr-2 text-gray-500 flex-shrink-0"
          />
          <label className="truncate">{label}</label>
        </div>
        <div className={fieldClasses}>{displayValue}</div>
      </div>
    );
  };

  const renderHistoryContent = () => {
    if (historyLoading) {
      return (
        <div className="flex justify-center items-center py-8">
          <div className="text-gray-500">Loading history...</div>
        </div>
      );
    }

    if (!history || history.length === 0) {
      return (
        <div className="text-center py-8 text-gray-500">
          <Clock size={48} className="mx-auto mb-4 text-gray-300" />
          <p>No history entries found for this ticket</p>
        </div>
      );
    }

    return (
      <div className="space-y-3">
        {history.map((entry) => (
          <div
            key={entry.history_id}
            className="border-l-2 border-gray-200 pl-4 pb-4"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div
                  className="text-sm font-medium text-gray-900"
                  dangerouslySetInnerHTML={{ __html: entry.title }}
                />
                <div className="text-xs text-gray-500 mt-1">
                  by {entry.modified_by || entry.created_by} •{" "}
                  {formatDate(entry.modified_at)}
                </div>
              </div>
              <div className="ml-4">
                <Clock size={14} className="text-gray-400" />
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  };

  // Show loading state
  if (loading) {
    return (
      <div className="flex h-screen bg-gray-100">
        <div
          className={`fixed md:static top-0 left-0 h-full z-30 transition-transform duration-300 ease-in-out ${isSidebarOpen
              ? "translate-x-0"
              : "-translate-x-full md:translate-x-0"
            }`}
        >
          <Sidebar />
        </div>
        <div className="flex-1 flex justify-center items-center">
          <div className="text-xl font-semibold">Loading ticket details...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-white">
      {/* Sidebar */}
      {isSidebarOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-20 md:hidden"
          onClick={toggleSidebar}
        />
      )}
      <div
        className={`fixed md:static top-0 left-0 h-full z-30 transition-transform duration-300 ease-in-out ${isSidebarOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
          }`}
      >
        <Sidebar />
      </div>

      <div className="flex flex-col flex-1 max-h-screen overflow-hidden">
        {/* Sub Header - Compact */}
        <div className="bg-white border-b flex items-start justify-between p-2 shadow-sm min-h-[60px]">
          <div className="flex items-start flex-1 min-w-0 mr-4">
            <button
              className="p-1 border mr-2 hover:bg-gray-100 flex-shrink-0 mt-1"
              onClick={() => navigate(-1)}
            >
              <ChevronLeft size={16} />
            </button>
            <span className="px-1 text-gray-500 flex-shrink-0 mt-1">≡</span>
            <div className="min-w-0 flex-1">
              <div className="font-semibold text-base leading-tight break-words pr-2">
                {ticket?.summary}
              </div>
              <div className="text-gray-600 text-xs mt-1">
                {ticket?.ticket_id}
              </div>
            </div>
          </div>

          {/* Buttons Container - Fixed Width and Aligned to Top */}
          <div className="flex items-start space-x-2 flex-shrink-0 mt-1">
            {ticket.status === "Resolved" ? (
              <button
                type="button"
                className="border px-4 py-2 text-xs bg-green-50 text-green-700 hover:bg-green-100 whitespace-nowrap rounded"
              >
                Resolved
              </button>
            ) : (
              <>
                {/* Conditional buttons based on assignee */}
                {ticket?.assignee?.toLowerCase() ===
                  userProfile?.username?.toLowerCase() && (
                    <>
                      {editableStatus !== "Working in Progress" ? (
                        <button
                          type="button"
                          className="border px-4 py-2 text-xs bg-gray-50 text-gray-700 hover:bg-gray-100 whitespace-nowrap rounded"
                          onClick={handleStartWork}
                        >
                          Start Work
                        </button>
                      ) : (
                        <button
                          type="button"
                          className="border px-4 py-2 text-xs bg-blue-50 text-blue-700 hover:bg-blue-100 whitespace-nowrap rounded"
                          onClick={handleQuestionToUser}
                        >
                          User Inputs
                        </button>
                      )}
                    </>
                  )}

                {/* Default buttons - always show */}

                <div className="p-6 max-w-md mx-auto bg-white rounded-lg shadow-md">
                  <h2 className="text-xl font-bold mb-4 text-center text-gray-800">
                    SLA Countdown Timer
                  </h2>
                  <div className="text-center">
                    <div
                      className={`text-4xl font-mono font-bold mb-2 ${slaExpired ? "text-red-600" : "text-blue-600"
                        }`}
                    >
                      {slaExpired ? "SLA Expired" : formatSLA(remainingSeconds)}
                    </div>
                    <div className="text-gray-500 text-sm">
                      <strong>Status:</strong> {slaStatus}
                    </div>
                    {slaExpired && (
                      <div className="text-red-600 font-semibold">Time Expired!</div>
                    )}
                  </div>
                </div>
                <button
                  type="button"
                  className="border px-4 py-2 text-xs bg-gray-50 text-gray-700 hover:bg-gray-100 whitespace-nowrap rounded"
                  onClick={handleAssignClick}
                >
                  Assign
                </button>
                <button
                  type="button"
                  className="border px-4 py-2 text-xs bg-gray-50 text-gray-700 hover:bg-gray-100 whitespace-nowrap rounded"
                  onClick={handleChangePriority}
                >
                  Change Priority
                </button>
                <button
                  type="button"
                  className="border px-4 py-2 text-xs bg-gray-50 text-gray-700 hover:bg-gray-100 whitespace-nowrap rounded"
                  onClick={handleCloseTicket}
                >
                  Close
                </button>
              </>
            )}
          </div>
        </div>

        {/* Main content area with scrolling */}
        <div className="flex-1 overflow-auto" ref={mainContentRef}>
          {/* Ticket Details Card */}
          <div className="bg-white p-3  shadow-sm m-3">
            {/* Key details in 2 columns for better space utilization */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-x-6 gap-y-1">
              {/* Column 1 */}
              <div>
                {renderField("Incident Number", ticket?.ticket_id)}
                {renderField("Service Domain", ticket?.service_domain)}
                {renderField("Service Type", ticket?.service_type)}
                {ticket?.created_by !== ticket?.on_behalf_of ? (
                  <>
                    {renderField("Requestor", ticket?.created_by)}
                    {renderField("On Behalf Req", ticket?.on_behalf_of)}
                  </>
                ) : (
                  renderField("Requestor", ticket?.created_by)
                )}

                {ticket?.solution_grp &&
                  renderField("Solution Group", ticket?.solution_grp)}
                {renderField("Assignee", ticket?.assignee)}
                {/* {ticket?.contact_mode === "phone" &&
                  renderField("Contact Number", ticket?.customer_number)} */}
              </div>

              {/* Column 2 */}
              <div>
                {renderField("Status", editableStatus)}
                {renderField("Impact", ticket?.impact)}
                {renderField("Priority", ticket?.priority)}
                {ticket?.project && renderField("Project", ticket?.project)}
                {ticket?.project_owner_email &&
                  renderField("Product", ticket?.project_owner_email)}
                {renderField(
                  "Created On",
                  formatDate(ticket?.created_at) || "N/A"
                )}
                {renderField(
                  "Updated On",
                  formatDate(ticket?.modified_at) || "N/A"
                )}
              </div>
            </div>

            {/* Reference Ticket - if exists */}
            {ticket?.reference_tickets &&
              ticket.reference_tickets.length > 0 && (
                <div className="flex items-center mt-2">
                  <label className="w-36 text-black text-sm font-medium">
                    Reference Ticket
                  </label>
                  <div className="border  px-2 py-1 text-sm bg-gray-50 flex-1">
                    {ticket.reference_tickets.join(", ")}
                  </div>
                </div>
              )}

            {/* Summary and Description - Compact */}
            <div className="flex max-w-[87.7%]">
              <div className="flex items-center w-[14%] text-gray-600 text-base pr-2">
                <FileText size={16} className="mr-2 text-gray-500" />
                <label>Description</label>
              </div>
              <div
                className="border px-2 py-1 text-sm flex-1 bg-gray-50 max-h-80 overflow-auto break-words break-all [&_a]:text-blue-500 [&_a]:underline [&_a]:cursor-pointer"
                dangerouslySetInnerHTML={{
                  __html: ticket?.description || "No description provided",
                }}
                onClick={(e) => {
                  if (e.target.tagName === "A") {
                    e.preventDefault();
                    let href = e.target.getAttribute("href");

                    // Check if it's already a full URL
                    if (
                      href &&
                      !href.startsWith("http://") &&
                      !href.startsWith("https://")
                    ) {
                      // If it doesn't start with protocol, add https://
                      href = "https://" + href;
                    }

                    if (href) {
                      window.open(href, "_blank", "noopener,noreferrer");
                    }
                  }
                }}
              ></div>
            </div>
          </div>

          {/* Professional Tab System */}
          <div className="sticky top-0 bg-white z-20 px-3 border-b shadow-sm">
            <div className="flex">
              {tabs.map((tab) => (
                <button
                  key={tab}
                  className={`px-4 py-2 font-medium relative transition-all duration-200 ${currentTab === tab
                      ? "text-blue-700"
                      : "text-gray-600 hover:text-gray-800"
                    }`}
                  onClick={() => setCurrentTab(tab)}
                >
                  {tab}
                  {currentTab === tab && (
                    <div className="absolute bottom-0 left-0 w-full h-0.5 bg-blue-700"></div>
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Tab Content with reference for scrolling */}
          <div className="p-4 bg-white" ref={tabContentRef}>
            {currentTab === "Notes" && (
              <div className="flex flex-col h-[400px] border rounded bg-white">
                <div className="flex-1 overflow-y-auto p-2" style={{ minHeight: 0 }}>
                  {chatMessages.length === 0 ? (
                    <div className="text-gray-400 text-center mt-8">No messages yet.</div>
                  ) : (
                    chatMessages.map((msg) => (
                      <div key={msg.id || msg.created_at} className="mb-3">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-blue-700">{msg.user?.username || "User"}</span>
                          <span className="text-xs text-gray-400">{formatDate(msg.created_at)}</span>
                        </div>
                        <div className="ml-2 text-gray-800">{msg.message}</div>
                      </div>
                    ))
                  )}
                </div>
                <div className="flex p-2 border-t">
                  <input
                    type="text"
                    className="flex-1 border rounded px-2 py-1"
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    placeholder="Type your message..."
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        sendChatMessage();
                      }
                    }}
                  />
                  <button
                    type="button"
                    className="ml-2 px-4 py-1 bg-blue-600 text-white rounded"
                    onClick={sendChatMessage}
                  >
                    Send
                  </button>
                </div>
              </div>
            )}

            {currentTab === "History" && renderHistoryContent()}

            {currentTab === "RelatedRecords" && (
              <div className="p-2">
                <div>
                  <div className="flex justify-between items-center mb-3">
                    <h3 className="font-medium text-lg">Attachments</h3>
                  </div>

                  <div className="border">
                    {/* Attachments Table */}
                    <table className="w-full">
                      <thead className="bg-gray-100">
                        <tr>
                          <th className="border-b p-2 text-left">File</th>
                          <th className="border-b p-2 text-left">
                            Uploaded At
                          </th>
                          <th className="border-b p-2 text-left">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {attachments && attachments.length > 0 ? (
                          attachments.map((attachment) => {
                            // Extract filename from the file path
                            const fileName = attachment.file.split("/").pop();
                            const fileExtension = fileName
                              .split(".")
                              .pop()
                              ?.toLowerCase();

                            // Define file type categories
                            const imageExtensions = [
                              "jpg",
                              "jpeg",
                              "png",
                              "gif",
                              "bmp",
                              "webp",
                              "svg",
                              "ico",
                            ];
                            const previewableDocuments = [
                              "pdf",
                              "txt",
                              "html",
                              "htm",
                              "json",
                              "xml",
                              "css",
                              "js",
                              "md",
                            ];
                            const nonPreviewableFiles = [
                              "docx",
                              "doc",
                              "xlsx",
                              "xls",
                              "pptx",
                              "ppt",
                              "zip",
                              "rar",
                              "7z",
                              "tar",
                              "gz",
                              "exe",
                              "dmg",
                              "apk",
                              "deb",
                              "rpm",
                            ];

                            // Determine file type
                            const isImage =
                              imageExtensions.includes(fileExtension);
                            const isPreviewableDocument =
                              previewableDocuments.includes(fileExtension);
                            const isNonPreviewable =
                              nonPreviewableFiles.includes(fileExtension);

                            // Construct the correct backend URL
                            const backendUrl =
                              process.env.REACT_APP_API_BASE_URL ||
                              "http://192.168.1.12:8000";
                            const fullUrl = `${backendUrl}${attachment.file}`;

                            return (
                              <tr
                                key={attachment.id}
                                className="hover:bg-gray-50"
                              >
                                <td className="border-b p-2">
                                  <div className="flex items-center">
                                    <Paperclip
                                      size={16}
                                      className="mr-2 text-gray-500"
                                    />
                                    <span className="text-gray-700">
                                      {fileName}
                                    </span>
                                  </div>
                                </td>
                                <td className="border-b p-2">
                                  {new Date(
                                    attachment.uploaded_at
                                  ).toLocaleString()}
                                </td>
                                <td className="border-b p-2">
                                  <div className="flex space-x-2">
                                    {/* Images: Only View (no download) */}
                                    {isImage && (
                                      <a
                                        href={fullUrl}
                                        className="text-blue-500 hover:underline"
                                        target="_blank"
                                        rel="noopener noreferrer"
                                      >
                                        View
                                      </a>
                                    )}

                                    {/* Previewable Documents: Both View and Download */}
                                    {isPreviewableDocument && (
                                      <>
                                        <a
                                          href={fullUrl}
                                          className="text-blue-500 hover:underline"
                                          target="_blank"
                                          rel="noopener noreferrer"
                                        >
                                          View
                                        </a>
                                        <a
                                          href={fullUrl}
                                          className="text-blue-500 hover:underline"
                                          download={fileName}
                                        >
                                          Download
                                        </a>
                                      </>
                                    )}

                                    {/* Non-previewable Files: Only Download */}
                                    {(isNonPreviewable ||
                                      (!isImage && !isPreviewableDocument)) && (
                                        <a
                                          href={fullUrl}
                                          className="text-blue-500 hover:underline"
                                          download={fileName}
                                        >
                                          Download
                                        </a>
                                      )}
                                  </div>
                                </td>
                              </tr>
                            );
                          })
                        ) : (
                          <tr>
                            <td
                              colSpan="3"
                              className="p-4 text-center text-gray-500"
                            >
                              No attachments found for this ticket
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}
            {currentTab === "ResolutionInfo" && (
              <ResolutionInfo ticketDetails={ticket} />
            )}
          </div>
        </div>

        <QuestionToUserModal
          isOpen={isQuestionModalOpen}
          onClose={() => setIsQuestionModalOpen(false)}
          ticketId={ticket?.ticket_id}
          ticketStatus={editableStatus}
          updateTicketStatus={updateTicketStatus}
          refreshChatMessages={() => {
            if (
              chatUIRef.current &&
              typeof chatUIRef.current.fetchMessages === "function"
            ) {
              chatUIRef.current.fetchMessages(ticket.ticket_id);
            }
          }}
          onQuestionSent={async () => {
            // fetchSLADetails();

            const success = await setNewStatus("Waiting for User Response");

            if (!success) {
              console.warn("Failed to pause SLA, not stopping timer.");
              return;
            }
            stopSLATimer();
            setSlaStatus("Paused");
            handleChatUpdate("Question sent to user", "question");



          }}
        />

        <AssignmentModal
          isOpen={isAssignmentModalOpen}
          onClose={() => setIsAssignmentModalOpen(false)}
          ticket={ticket}
          onAssignmentSuccess={handleAssignmentSuccess}
        />

        <PriorityModal
          isOpen={isPriorityModalOpen}
          onClose={() => setIsPriorityModalOpen(false)}
          ticket={ticket}
          refetchTicketDetails={refetchTicketDetails}
        />

        <CloseTicketModal
          isOpen={isCloseModalOpen}
          onClose={() => setIsCloseModalOpen(false)}
          onConfirm={handleConfirmClose}
        />

        {/* Toast Container and Chatbot */}
        <ChatbotPopup />
        <ToastContainer
          position="top-right"
          autoClose={3000}
          hideProgressBar={false}
          newestOnTop={false}
          closeOnClick
          rtl={false}
          pauseOnFocusLoss
          draggable
          pauseOnHover
          style={{ fontSize: "14px" }}
        />
      </div>
    </div>
  );
}
