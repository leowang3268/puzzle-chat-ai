// scripts.js

// --- 1. Configuration ---
const WEBSOCKET_URL_BASE = '7ddd-118-150-67-211.ngrok-free.app';
const MODE = "A"; // A, B, C, or D

const userName = sessionStorage.getItem('userName');
if (!userName) {
    // Redirect to login or prompt for username if not set
    // For now, let's use a default for testing
    // window.location.href = '/login.html'; 
}

// --- 2. DOM Elements ---
const DOMElements = {
    container: document.getElementById('container'),
    leftSpace: document.getElementById('left-space'),
    resizer: document.getElementById('resizer'),
    // User Chat
    userChat: {
        form: document.getElementById('form'),
        messageBox: document.getElementById('messageBox'),
        messagesContainer: document.getElementById('messages'),
        replyContainer: document.getElementById('reply-container'),
        userMessageTemplate: document.getElementById('user-message-template'),
    },
    // AI Chat
    aiChat: {
        form: document.getElementById('ai-form'),
        messageBox: document.getElementById('ai-messageBox'),
        messagesContainer: document.getElementById('ai-messages'),
    },
    // Shared Content
    sharedContent: {
        container: document.getElementById('shared-container'),
        messagesContainer: document.getElementById('shared-messages'),
        defaultMsg: document.getElementById('default-shared-msg'),
        title: document.getElementById('ai-other-title'),
        optionsButton: document.getElementById('shared-option-button'),
        optionsPanel: document.getElementById('shared-content-options'),
        optionsContainer: document.querySelector('.shared-option-container'),
    }
};

// --- 3. WebSocket Logic ---
const chatSocket = new WebSocket(`wss://${WEBSOCKET_URL_BASE}/ws/socket-server/?userName=${userName}`);

chatSocket.onopen = () => {
    console.log('WebSocket connection established.');
    chatSocket.send(JSON.stringify({ type: 'user_connect', userName }));
    initializeUIBasedOnMode();
};

chatSocket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    // Message router
    switch (data.type) {
        case 'chat':
            handleUserChatMessage(data);
            break;
        case 'ai_chat':
            handleAIChatMessage(data);
            break;
        case 'load_ai_chat':
            loadAIChatMessage(data);
            break;
        case 'notify_have_read':
            markMessagesAsRead(data.chatWith);
            break;
        case 'notify_typing':
            showTypingIndicator(data.chatWith, data.typing_message);
            break;
        case 'stop_typing':
            hideTypingIndicator(data.chatWith);
            break;
        case 'update_thumb_count':
            updateThumbCount(data.message_index, data.thumb_count);
            break;
        default:
            console.warn('Unknown message type:', data.type);
    }
};

chatSocket.onclose = () => {
    console.log('WebSocket connection closed.');
    // Optionally send disconnect message, though it might fail if connection is already severed
};

chatSocket.onerror = (error) => {
    console.error('WebSocket Error:', error);
};

// --- 4. Event Listeners ---

// User Chat Form
DOMElements.userChat.form.addEventListener('submit', (e) => {
    e.preventDefault();
    sendMessageToUser();
});

DOMElements.userChat.messageBox.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessageToUser();
    }
});

// AI Chat Form
DOMElements.aiChat.form.addEventListener('submit', (e) => {
    e.preventDefault();
    sendMessageToAI();
});

DOMElements.aiChat.messageBox.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessageToAI();
    }
});

// Auto-resize textareas
[DOMElements.userChat.messageBox, DOMElements.aiChat.messageBox].forEach(textarea => {
    textarea.addEventListener('input', function () {
        this.style.height = 'auto';
        this.style.height = `${this.scrollHeight}px`;
    });
});

// Typing indicator
DOMElements.userChat.messageBox.addEventListener('input', () => {
    chatSocket.send(JSON.stringify({
        type: 'typing',
        userName: userName,
        typing_message: DOMElements.userChat.messageBox.value
    }));
});

// Mark messages as read when clicking chatroom
DOMElements.userChat.messagesContainer.parentElement.addEventListener('click', () => {
    chatSocket.send(JSON.stringify({ type: 'mark_all_read', userName }));
});


// Resizer Logic
let isResizing = false;
DOMElements.resizer.addEventListener("mousedown", () => {
    isResizing = true;
    document.body.style.cursor = "ew-resize";
    document.addEventListener("mousemove", resize);
    document.addEventListener("mouseup", stopResize);
});

function resize(e) {
    if (!isResizing) return;
    const containerRect = DOMElements.container.getBoundingClientRect();
    const newLeftWidth = e.clientX - containerRect.left;
    if (newLeftWidth >= 200 && newLeftWidth <= containerRect.width - 200) {
        DOMElements.leftSpace.style.flex = `0 0 ${newLeftWidth}px`;
    }
}

function stopResize() {
    isResizing = false;
    document.body.style.cursor = "default";
    document.removeEventListener("mousemove", resize);
    document.removeEventListener("mouseup", stopResize);
}


// Share options panel toggle
DOMElements.sharedContent.optionsButton.addEventListener('click', (e) => {
    e.stopPropagation();
    const panel = DOMElements.sharedContent.optionsPanel;
    panel.style.display = panel.style.display === 'block' ? 'none' : 'block';
});

document.addEventListener('click', (e) => {
    if (!DOMElements.sharedContent.optionsPanel.contains(e.target) && e.target !== DOMElements.sharedContent.optionsButton) {
        DOMElements.sharedContent.optionsPanel.style.display = 'none';
    }
});


// Context Menu for replying
DOMElements.userChat.messagesContainer.addEventListener('contextmenu', (e) => {
    const messageP = e.target.closest('p.current_message');
    if (messageP) {
        e.preventDefault();
        showCustomContextMenu(e, messageP.textContent);
    }
});


// --- 5. Core Functions (Message Handling) ---

function sendMessageToUser() {
    const message = DOMElements.userChat.messageBox.value.trim();
    if (!message) return;

    const replyContainer = DOMElements.userChat.replyContainer;
    let replyText = '';
    if (replyContainer.style.display === 'block') {
        replyText = replyContainer.dataset.replyText || '';
    }

    chatSocket.send(JSON.stringify({
        type: 'chat',
        userName,
        message,
        replyText
    }));

    DOMElements.userChat.messageBox.value = '';
    DOMElements.userChat.messageBox.style.height = 'auto';
    hideReplyPreview();
}

function sendMessageToAI() {
    const message = DOMElements.aiChat.messageBox.value.trim();
    if (!message) return;

    const sharedOptions = Array.from(document.querySelectorAll('input[name="sharedOption"]:checked'))
                               .map(checkbox => checkbox.value);

    // Show user's message immediately
    appendAIMessage(userName, message);
    // Show waiting indicator
    appendAIMessage('ai', '...', true); 
    
    chatSocket.send(JSON.stringify({
        type: 'ai_chat',
        userName,
        ai_message: message,
        mode: MODE,
        sharedOptions
    }));

    DOMElements.aiChat.messageBox.value = '';
    DOMElements.aiChat.messageBox.style.height = 'auto';
}


function handleUserChatMessage(data) {
    const { userName: senderName, message, replyText, liked_by } = data;
    hideTypingIndicator(senderName);
    
    const messageIndex = DOMElements.userChat.messagesContainer.querySelectorAll('.message').length;

    const element = createUserMessageElement({
        senderName,
        message,
        replyText,
        liked_by,
        messageIndex
    });
    
    DOMElements.userChat.messagesContainer.appendChild(element);
    scrollToBottom(DOMElements.userChat.messagesContainer);
}

function handleAIChatMessage(data) {
    const { userName: sender, user_message, ai_reply_content, ai_user_summary, send_in_mode_c } = data;

    // If the message is from the current user, it means this is the AI's reply.
    if (userName === sender) {
        // Remove waiting dots and append the actual AI reply
        const waitingDots = DOMElements.aiChat.messagesContainer.querySelector('.waiting-dots');
        if (waitingDots) waitingDots.closest('.ai-message').remove();
        appendAIMessage('ai', ai_reply_content);
    } else { // Message is from the other user for the shared view
        updateSharedContent({ user_message, ai_reply_content, ai_user_summary, send_in_mode_c });
    }
}

function loadAIChatMessage(data) {
    const { userName: sender, user_message, ai_reply_content, ai_user_summary, send_in_mode_c } = data;
    if (userName === sender) {
        appendAIMessage(sender, user_message);
        appendAIMessage('ai', ai_reply_content);
    } else {
        updateSharedContent({ user_message, ai_reply_content, ai_user_summary, send_in_mode_c });
    }
}


// --- 6. UI & Helper Functions ---

function initializeUIBasedOnMode() {
    const title = DOMElements.sharedContent.title;
    let tooltipText = "";
    let titleText = "";
    
    switch (MODE) {
        case "A":
            titleText = "Others & AI 的對話";
            tooltipText = "此處呈現另一位使用者與AI討論的情況。";
            break;
        case "B":
        case "C":
            titleText = "Others & AI 的對話摘要";
            tooltipText = "此處總結另一位使用者與AI討論的結果。";
            break;
        case "D":
            DOMElements.sharedContent.container.style.display = 'none';
            break;
    }
    
    title.innerHTML = `<span class="tooltip-icon" data-tooltip="${tooltipText}"></span> ${titleText}`;
    
    if (MODE !== "C") {
        DOMElements.sharedContent.optionsContainer.style.display = 'none';
    }
}

/**
 * Creates a user message element from a template.
 * @param {object} data - The message data.
 * @returns {HTMLElement} The created message element.
 */
function createUserMessageElement(data) {
    const { senderName, message, replyText, liked_by, messageIndex } = data;
    const template = DOMElements.userChat.userMessageTemplate.content.cloneNode(true);
    const element = template.querySelector('.message');

    // Set class for own/other/common messages
    if (senderName === userName) {
        element.classList.add('own');
    } else if (senderName === "ai") { // Example for system messages
        element.classList.add('common');
    } else {
        element.classList.add('other');
    }
    
    element.dataset.index = messageIndex;

    // Handle reply
    if (replyText) {
        const replyContentDiv = element.querySelector('.reply-content');
        replyContentDiv.innerHTML = replyText.replace(/\n/g, '<br />');
        element.querySelector('p.current_message').style.borderRadius = "0 0 10px 10px";
    }

    // Set message text
    element.querySelector('p.current_message').innerHTML = message.replace(/\n/g, '<br />');
    
    // Handle likes
    const thumbIcon = element.querySelector('.thumb-icon');
    const thumbCount = element.querySelector('.thumb-count');
    const hasLiked = liked_by.includes(userName);
    
    thumbCount.textContent = liked_by.length;
    thumbIcon.classList.toggle('blue', hasLiked);
    thumbIcon.classList.toggle('gray', !hasLiked);

    return element;
}

/**
 * Appends a message to the AI chat window.
 * @param {string} sender - 'user' or 'ai'.
 * @param {string} content - The message content.
 * @param {boolean} isWaiting - If true, adds a waiting animation class.
 */
function appendAIMessage(sender, content, isWaiting = false) {
    const container = DOMElements.aiChat.messagesContainer;
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('ai-message');
    
    if (sender === userName) {
        messageDiv.classList.add('own');
    } else {
        messageDiv.classList.add('other');
    }

    const p = document.createElement('p');
    p.innerHTML = content.replace(/\n/g, '<br />').replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');

    if (isWaiting) {
        p.classList.add('waiting-dots');
    }
    
    messageDiv.appendChild(p);
    container.appendChild(messageDiv);
    scrollToBottom(container);
}

function updateSharedContent({ user_message, ai_reply_content, ai_user_summary, send_in_mode_c }) {
    if (DOMElements.sharedContent.defaultMsg) {
        DOMElements.sharedContent.defaultMsg.remove();
        DOMElements.sharedContent.defaultMsg = null;
    }

    let contentHTML = '';
    switch (MODE) {
        case 'A':
            contentHTML = `
                <div class="shared-message own"><p>${user_message.replace(/\n/g, '<br />')}</p></div>
                <div class="shared-message other"><p>${ai_reply_content.replace(/\n/g, '<br />')}</p></div>
            `;
            break;
        case 'B':
            contentHTML = `<div class="shared-message common"><p>${ai_user_summary.replace(/\n/g, '<br />')}</p></div>`;
            break;
        case 'C':
            if (send_in_mode_c === "yes") {
                contentHTML = `<div class="shared-message common"><p>${ai_user_summary.replace(/\n/g, '<br />')}</p></div>`;
            }
            break;
    }
    
    DOMElements.sharedContent.messagesContainer.insertAdjacentHTML('beforeend', contentHTML);
    scrollToBottom(DOMElements.sharedContent.messagesContainer);
}


function showTypingIndicator(typingUser, message) {
    if (typingUser === userName) return;

    hideTypingIndicator(typingUser); // Remove old one first

    if (message === '') return;

    const html = `
        <div class="message other typing-indicator-wrapper">
            <p class="typing-indicator">${message.replace(/\n/g, '<br />')}</p>
        </div>`;
    DOMElements.userChat.messagesContainer.insertAdjacentHTML('beforeend', html);
    scrollToBottom(DOMElements.userChat.messagesContainer);
}

function hideTypingIndicator(typingUser) {
    if (typingUser === userName) return;
    const indicator = DOMElements.userChat.messagesContainer.querySelector('.typing-indicator-wrapper');
    if (indicator) indicator.remove();
}


function showCustomContextMenu(event, messageText) {
    // Remove any existing menu
    const existingMenu = document.querySelector('.context-menu');
    if (existingMenu) existingMenu.remove();

    const contextMenu = document.createElement('div');
    contextMenu.className = 'context-menu';
    contextMenu.innerHTML = `<li class="context-menu-item">回覆</li>`;
    
    contextMenu.querySelector('li').addEventListener('click', () => {
        showReplyPreview(messageText);
        contextMenu.remove();
    });

    document.body.appendChild(contextMenu);
    contextMenu.style.top = `${event.pageY}px`;
    contextMenu.style.left = `${event.pageX}px`;

    // Close on next click
    setTimeout(() => document.addEventListener('click', () => contextMenu.remove(), { once: true }), 0);
}

function showReplyPreview(messageText) {
    const container = DOMElements.userChat.replyContainer;
    container.style.display = 'block';
    container.dataset.replyText = messageText; // Store full text
    
    // Truncate for display
    const previewText = messageText.length > 50 ? messageText.substring(0, 50) + '...' : messageText;
    container.innerHTML = `回覆: ${previewText} <span id="close-reply">x</span>`;

    container.querySelector('#close-reply').addEventListener('click', (e) => {
        e.stopPropagation();
        hideReplyPreview();
    });
}

function hideReplyPreview() {
    const container = DOMElements.userChat.replyContainer;
    container.style.display = 'none';
    container.textContent = '';
    container.dataset.replyText = '';
}

function toggleThumb(element) {
    const messageElement = element.closest('.message');
    const messageIndex = messageElement.dataset.index;
    const isPressed = element.classList.contains('gray'); // if gray, it means it's about to be pressed
    
    chatSocket.send(JSON.stringify({
        type: 'thumb_press',
        userName,
        index: messageIndex,
        pressed: isPressed
    }));
}

function updateThumbCount(messageIndex, thumbCount, likers) {
    const messageElement = document.querySelector(`.message[data-index="${messageIndex}"]`);
    if (!messageElement) return;

    const thumbCountElement = messageElement.querySelector('.thumb-count');
    const thumbIcon = messageElement.querySelector('.thumb-icon');
    
    if (thumbCountElement) thumbCountElement.textContent = thumbCount;
    
    // This is a simplified update. A full implementation would receive the list of 'likers'
    // and check if the current user is in it to update the color. The backend logic handles the source of truth.
}


function markMessagesAsRead(notifiedPerson) {
    if (userName === notifiedPerson) {
        const ownMessages = document.querySelectorAll('.message.own');
        ownMessages.forEach(msg => {
            if (!msg.querySelector('.read-status')) {
                const status = document.createElement('span');
                status.className = 'read-status';
                status.textContent = '已讀';
                msg.insertBefore(status, msg.firstChild);
            }
        });
    }
}

function scrollToBottom(element) {
    element.scrollTop = element.scrollHeight;
}