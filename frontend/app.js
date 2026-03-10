(function () {
  var messagesEl = document.getElementById("messages");
  var container = document.getElementById("messages-container");
  var messageInput = document.getElementById("message-input");
  var sendBtn = document.getElementById("send-btn");
  var apiUrlInput = document.getElementById("api-url");
  var phoneInput = document.getElementById("phone");

  function addMessage(role, text) {
    var time = new Date().toLocaleTimeString("es-CL", {
      hour: "2-digit",
      minute: "2-digit",
    });

    var div = document.createElement("div");
    div.className = "message " + (role === "user" ? "sent" : "received");

    var bubble = document.createElement("div");
    bubble.className = "message-bubble";

    var content = document.createElement("div");
    content.className = "message-content";
    content.textContent = text;

    var timeEl = document.createElement("div");
    timeEl.className = "message-time";
    timeEl.textContent = time;

    bubble.appendChild(content);
    bubble.appendChild(timeEl);
    div.appendChild(bubble);
    messagesEl.appendChild(div);

    container.scrollTop = container.scrollHeight;
  }

  async function send() {
    var text = (messageInput.value || "").trim();
    if (!text) return;

    var apiUrl = (apiUrlInput.value || "").trim().replace(/\/$/, "");
    var phone = (phoneInput.value || "").trim();

    if (!apiUrl || !phone) {
      addMessage("assistant", "Configura API URL y teléfono arriba.");
      return;
    }

    messageInput.value = "";
    addMessage("user", text);
    sendBtn.disabled = true;

    try {
      const response = await fetch(apiUrl + "/webhook/whatsapp", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          from_number: phone,
          body: text,
        }),
      });

      const data = await response.json();

      if (data.reply) {
        addMessage("assistant", data.reply);
      }
    } catch (error) {
      console.error(error);
      addMessage("assistant", "Error conectando con la API ❌");
    } finally {
      sendBtn.disabled = false;
    }
  }

  sendBtn.addEventListener("click", send);

  messageInput.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  });
})();
