// scripts.js - 整合版 (2025-07-13)

// --- 1. 組態設定 (Configuration) ---
const WEBSOCKET_URL_BASE = '6e672cd2bda4.ngrok-free.app'; // 請替換成您的 ngrok 或伺服器位址
const MODE = "C"; // 可選模式: A, B, C。

const userName = sessionStorage.getItem('userName');
if (!userName) {
    alert("無法獲取使用者名稱，請先登入！");
    window.location.href = '/';
}

if (typeof roomName === 'undefined' || !roomName) {
    alert("錯誤：無法從頁面獲取房間名稱！");
    console.error("全域變數 roomName 未定義。");
}


// --- 2. DOM 元素快取 ---
const DOMElements = {
    container: document.getElementById('container'),
    leftSpace: document.getElementById('left-space'),
    resizer: document.getElementById('resizer'),
    userChat: {
        form: document.getElementById('form'),
        messageBox: document.getElementById('messageBox'),
        messagesContainer: document.getElementById('messages'),
        replyContainer: document.getElementById('reply-container'),
        userMessageTemplate: document.getElementById('user-message-template'),
    },
    aiChat: {
        form: document.getElementById('ai-form'),
        messageBox: document.getElementById('ai-messageBox'),
        messagesContainer: document.getElementById('ai-messages'),
    },
    sharedContent: {
        container: document.getElementById('shared-container'),
        messagesContainer: document.getElementById('shared-messages'),
        defaultMsg: document.getElementById('default-shared-msg'),
        title: document.getElementById('ai-other-title'),
        optionsButton: document.getElementById('shared-option-button'),
        optionsPanel: document.getElementById('shared-content-options'),
        optionsContainer: document.querySelector('.shared-option-container'),
    },
    suggestion: {
        container: document.getElementById('suggestion-container'),
        text: document.getElementById('suggestion-text'),
        sendBtn: document.getElementById('send-suggestion-btn'),
        dismissBtn: document.getElementById('dismiss-suggestion-btn'),
    }
};

// --- 3. 全域變數 ---
let tooltipElement = null;
let tooltipTimeout = null;

// --- 4. WebSocket 連線 ---
const chatSocket = new WebSocket(`wss://${WEBSOCKET_URL_BASE}/ws/socket-server/?userName=${userName}&roomName=${roomName}`);

chatSocket.onopen = () => {
    console.log('WebSocket connection established for room:', roomName);
    chatSocket.send(JSON.stringify({ type: 'user_connect', userName }));
    initializeUIBasedOnMode(); // 初始化UI
};

chatSocket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log("Received data:", data);

    switch (data.type) {
        case 'chat': handleUserChatMessage(data); break;
        case 'ai_chat': handleAIChatMessage(data); break;
        case 'load_ai_chat': loadAIChatMessage(data); break;
        case 'notify_have_read': markMessagesAsRead(data.chatWith); break;
        case 'notify_typing': showTypingIndicator(data.typing_message); break;
        case 'stop_typing': hideTypingIndicator(); break;
        case 'update_thumb_count': updateThumbCount(data.message_index, data.thumb_count, data.likers); break;
        case 'game_over': handleGameOver(data); break;
        // ⭐ MODIFIED: Handle new 'ai_message_id' property
        case 'display_suggestion': showSuggestion(data.suggestion, data.ai_message_id); break;
        default: console.warn('Unknown message type:', data.type);
    }
};

chatSocket.onclose = () => { console.log('WebSocket connection closed.'); };
chatSocket.onerror = (error) => { console.error('WebSocket Error:', error); };

// --- 5. 事件監聽器 (Event Listeners) ---
DOMElements.userChat.form.addEventListener('submit', (e) => { e.preventDefault(); sendMessageToUser(); });
DOMElements.userChat.messageBox.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessageToUser(); } });
DOMElements.aiChat.form.addEventListener('submit', (e) => { e.preventDefault(); sendMessageToAI(); });
DOMElements.aiChat.messageBox.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessageToAI(); } });

[DOMElements.userChat.messageBox, DOMElements.aiChat.messageBox].forEach(textarea => {
    textarea.addEventListener('input', function () { this.style.height = 'auto'; this.style.height = `${this.scrollHeight}px`; });
});

DOMElements.userChat.messageBox.addEventListener('input', () => { chatSocket.send(JSON.stringify({ type: 'typing', userName: userName, typing_message: DOMElements.userChat.messageBox.value })); });
DOMElements.userChat.messagesContainer.parentElement.addEventListener('click', () => { chatSocket.send(JSON.stringify({ type: 'mark_all_read', userName })); });
DOMElements.userChat.messagesContainer.addEventListener('contextmenu', (e) => {
    const messageElement = e.target.closest('.message');
    if (messageElement) { e.preventDefault(); const messageP = messageElement.querySelector('p.current_message'); if (messageP) { const messageText = messageP.textContent; const messageAuthor = messageElement.dataset.author; showCustomContextMenu(e, messageText, messageAuthor); } }
});

let isResizing = false;
DOMElements.resizer.addEventListener("mousedown", (e) => { isResizing = true; document.body.style.cursor = "ew-resize"; document.addEventListener("mousemove", resize); document.addEventListener("mouseup", stopResize); });
DOMElements.sharedContent.container.addEventListener('click', () => { if (DOMElements.sharedContent.container.classList.contains('new-content-highlight')) { DOMElements.sharedContent.container.classList.remove('new-content-highlight'); } });
// ⭐ MODIFIED: Event listeners for suggestion buttons
DOMElements.suggestion.sendBtn.addEventListener('click', () => {
    const suggestionText = DOMElements.suggestion.text.textContent;
    // ⭐ NEW: Send feedback to server
    const aiMessageId = DOMElements.suggestion.container.dataset.aiMessageId;
    if (aiMessageId) {
        chatSocket.send(JSON.stringify({
            type: 'suggestion_sent',
            ai_message_id: parseInt(aiMessageId)
        }));
    }
    // End new code
    if (suggestionText) { DOMElements.userChat.messageBox.value = suggestionText; sendMessageToUser(); hideSuggestion(); DOMElements.userChat.messageBox.style.height = 'auto'; DOMElements.userChat.messageBox.style.height = `${DOMElements.userChat.messageBox.scrollHeight}px`; } });
DOMElements.suggestion.dismissBtn.addEventListener('click', () => {
    // ⭐ NEW: Send feedback to server
    const aiMessageId = DOMElements.suggestion.container.dataset.aiMessageId;
    if (aiMessageId) {
        chatSocket.send(JSON.stringify({
            type: 'suggestion_dismissed',
            ai_message_id: parseInt(aiMessageId)
        }));
    }
    // End new code
    hideSuggestion();
});
function resize(e) { if (!isResizing) return; const containerRect = DOMElements.container.getBoundingClientRect(); const newLeftWidth = e.clientX - containerRect.left; if (newLeftWidth >= 200 && newLeftWidth <= containerRect.width - 200) { DOMElements.leftSpace.style.flex = `0 0 ${newLeftWidth}px`; } }
function stopResize() { isResizing = false; document.body.style.cursor = "default"; document.removeEventListener("mousemove", resize); document.removeEventListener("mouseup", stopResize); }

// --- 6. 核心功能函式 (Core Functions) ---

function sendMessageToUser() {
    const message = DOMElements.userChat.messageBox.value.trim();
    if (!message) return;
    const replyContainer = DOMElements.userChat.replyContainer;
    let replyText = replyContainer.dataset.replyText || '';
    let replyAuthor = replyContainer.dataset.replyAuthor || '';
    chatSocket.send(JSON.stringify({ type: 'chat', userName, message, replyText, replyAuthor }));
    DOMElements.userChat.messageBox.value = '';
    DOMElements.userChat.messageBox.style.height = 'auto';
    hideReplyPreview();
}

function sendMessageToAI() {
    const message = DOMElements.aiChat.messageBox.value.trim();
    if (!message) return;
    appendAIMessage(userName, message);
    appendAIMessage('ai', '...', true);
    chatSocket.send(JSON.stringify({ type: 'ai_chat', userName, ai_message: message, mode: MODE }));
    DOMElements.aiChat.messageBox.value = '';
    DOMElements.aiChat.messageBox.style.height = 'auto';
}

function handleUserChatMessage(data) { hideTypingIndicator(); const messageIndex = DOMElements.userChat.messagesContainer.querySelectorAll('.message').length; const element = createUserMessageElement({ ...data, messageIndex }); DOMElements.userChat.messagesContainer.appendChild(element); scrollToBottom(DOMElements.userChat.messagesContainer); }
function handleAIChatMessage(data) {
    const { userName: sender, ai_reply_content } = data;

    // 處理自己送出的 AI 訊息的回覆
    if (userName === sender) {
        const waitingIndicator = DOMElements.aiChat.messagesContainer.querySelector('.ai-waiting-indicator');
        if (waitingIndicator) {
            // 不直接移除，而是替換內容，這樣更穩固
            const p = waitingIndicator.querySelector('p');
            if(p) {
                p.innerHTML = ai_reply_content.replace(/\n/g, '<br />').replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');
                p.style.display = 'block'; // 確保樣式正確
                p.style.alignItems = '';
            }
            waitingIndicator.classList.remove('ai-waiting-indicator');
        } else {
            // 如果因為某些原因找不到等待動畫（例如網路延遲），依然要能顯示回覆
            appendAIMessage('ai', ai_reply_content);
        }
    } 
    // 處理夥伴的 AI 訊息（主要用於 Mode A 的共享面板）
    else {
        updateSharedContent(data);
    }
}
function loadAIChatMessage(data) { const { userName: sender, user_message, ai_reply_content } = data; if (userName === sender) { appendAIMessage(sender, user_message); appendAIMessage('ai', ai_reply_content); } else { updateSharedContent(data); } }
function handleGameInfo(data) { const puzzleBox = document.getElementById('puzzle-question-text'); if (puzzleBox) { puzzleBox.textContent = data.puzzle_question; } }

// --- 7. UI 與輔助函式 (UI & Helper Functions) ---

// ⭐ START: UPDATED UI INITIALIZATION LOGIC ⭐
function initializeUIBasedOnMode() {
    const sharedContainer = DOMElements.sharedContent.container;
    const titleContainer = DOMElements.sharedContent.title;
    const sharedOptionsContainer = DOMElements.sharedContent.optionsContainer;

    if (!sharedContainer || !titleContainer || !sharedOptionsContainer) {
        console.error("關鍵 UI 元素未找到，無法初始化。");
        return;
    }

    // 隱藏目前版本中未使用的「分享設定」按鈕
    sharedOptionsContainer.style.display = 'none';

    switch (MODE) {
        case 'A':
            // 在 Mode A，確保「夥伴狀態」面板可見，並設定其標題
            sharedContainer.style.display = 'flex'; // 'flex' 是其預設的正確顯示樣式
            const titleText = "夥伴與AI的對話";
            const tooltipText = "此處即時顯示夥伴與AI裁判的完整問答。";
            const iconHTML = `<span class="tooltip-icon"></span>`;
            titleContainer.innerHTML = `${iconHTML} ${titleText}`;
            const icon = titleContainer.querySelector('.tooltip-icon');
            if (icon) {
                icon.addEventListener('mouseover', (e) => showTooltip(e.currentTarget, tooltipText));
                icon.addEventListener('mouseout', hideTooltip);
            }
            break;

        case 'B':
        case 'C':
            // 在 Mode B 和 C，隱藏整個「夥伴狀態」面板
            sharedContainer.style.display = 'none';
            break;

        default:
            // 對於任何未定義的模式，預設也將其隱藏
            sharedContainer.style.display = 'none';
            break;
    }
}
// ⭐ END: UPDATED UI INITIALIZATION LOGIC ⭐

// ⭐ MODIFIED: Update showSuggestion and hideSuggestion to handle the ID
function showSuggestion(suggestionText, aiMessageId) {
    if (!suggestionText || !DOMElements.suggestion.container) return;
    hideSuggestion(); 
    requestAnimationFrame(() => {
        DOMElements.suggestion.text.innerHTML = suggestionText.replace(/\n/g, '<br />').replace(/\*\*(.*?)\*\*/g, '<b>$1</b>');
        // ⭐ NEW: Store the ID on the element
        if (aiMessageId) {
            DOMElements.suggestion.container.dataset.aiMessageId = aiMessageId;
        }
        DOMElements.suggestion.container.style.display = 'flex';
    });
}

function hideSuggestion() {
    if (!DOMElements.suggestion.container) return;
    DOMElements.suggestion.container.style.display = 'none';
    DOMElements.suggestion.text.textContent = '';
    // ⭐ NEW: Clean up the stored ID
    if (DOMElements.suggestion.container.dataset.aiMessageId) {
        delete DOMElements.suggestion.container.dataset.aiMessageId;
    }
}
function createUserMessageElement(data) { const { userName: senderName, message, replyText, liked_by, messageIndex, replyAuthor } = data; const template = DOMElements.userChat.userMessageTemplate.content.cloneNode(true); const element = template.querySelector('.message'); element.dataset.author = senderName; element.dataset.index = messageIndex; const senderNameElement = element.querySelector('.message-sender-name'); if (senderName === userName) { element.classList.add('own'); senderNameElement.style.display = 'none'; } else { element.classList.add('other'); senderNameElement.textContent = senderName; senderNameElement.style.display = 'block'; } const replyContentDiv = element.querySelector('.reply-content'); if (replyText) { replyContentDiv.style.display = 'block'; replyContentDiv.innerHTML = `<p>${replyText.replace(/\n/g, '<br />')}</p>`; if (replyAuthor) { if (replyAuthor === userName) { replyContentDiv.classList.add('reply-to-own'); } else { replyContentDiv.classList.add('reply-to-other'); } } } else { replyContentDiv.style.display = 'none'; } element.querySelector('p.current_message').innerHTML = message.replace(/\n/g, '<br />'); const thumbIcon = element.querySelector('.thumb-icon'); const thumbCount = element.querySelector('.thumb-count'); const hasLiked = liked_by.includes(userName); thumbCount.textContent = liked_by.length; thumbIcon.classList.toggle('blue', hasLiked); thumbIcon.classList.toggle('gray', !hasLiked); return element; }
function appendAIMessage(sender, content, isWaiting = false) { const container = DOMElements.aiChat.messagesContainer; const template = document.getElementById('ai-message-template').content.cloneNode(true); const messageDiv = template.querySelector('.ai-message'); const p = messageDiv.querySelector('p'); messageDiv.classList.add(sender === userName ? 'own' : 'other'); if (isWaiting) { p.innerHTML = `<span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span>`; messageDiv.classList.add('ai-waiting-indicator'); p.style.display = 'flex'; p.style.alignItems = 'center'; } else { p.innerHTML = content.replace(/\n/g, '<br />').replace(/\*\*(.+?)\*\*/g, '<b>$1</b>'); } container.appendChild(messageDiv); scrollToBottom(container); }
function updateSharedContent(data) {
    if (MODE !== 'A') return; // 在 B 和 C 模式下，此面板無作用
    const { userName: sender, user_message, ai_reply_content } = data;
    const container = DOMElements.sharedContent.messagesContainer;
    if (DOMElements.sharedContent.defaultMsg) { DOMElements.sharedContent.defaultMsg.remove(); DOMElements.sharedContent.defaultMsg = null; }
    let contentHTML = '';
    if (user_message && ai_reply_content) { contentHTML = `<div class="shared-message-group"><div class="ai-message other"><strong class="message-sender-name">${sender}</strong><p>${user_message}</p></div><div class="ai-message own"><strong class="message-sender-name">AI 裁判</strong><p>${ai_reply_content}</p></div></div>`; }
    if (contentHTML) { container.insertAdjacentHTML('beforeend', contentHTML); const sharedContainer = DOMElements.sharedContent.container; if (sharedContainer && !sharedContainer.classList.contains('new-content-highlight')) { sharedContainer.classList.add('new-content-highlight'); } scrollToBottom(container); }
}
function showTypingIndicator(message) { hideTypingIndicator(); if (!message || message.trim() === '') return; const html = `<div class="message other typing-indicator-wrapper"><p style="display: flex; align-items: center;"><span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span></p></div>`; DOMElements.userChat.messagesContainer.insertAdjacentHTML('beforeend', html); scrollToBottom(DOMElements.userChat.messagesContainer); }
function hideTypingIndicator() { const indicators = document.querySelectorAll('.typing-indicator-wrapper'); indicators.forEach(indicator => indicator.remove()); }
function showCustomContextMenu(event, messageText, messageAuthor) { const existingMenu = document.querySelector('.context-menu'); if (existingMenu) existingMenu.remove(); const contextMenu = document.createElement('ul'); contextMenu.className = 'context-menu'; contextMenu.innerHTML = `<li class="context-menu-item">回覆</li>`; contextMenu.querySelector('li').addEventListener('click', () => { showReplyPreview(messageText, messageAuthor); DOMElements.userChat.messageBox.focus(); contextMenu.remove(); }); document.body.appendChild(contextMenu); const { offsetWidth: menuWidth, offsetHeight: menuHeight } = contextMenu; const { innerWidth: windowWidth, innerHeight: windowHeight } = window; let top = event.pageY, left = event.pageX; if (left + menuWidth > windowWidth) left = windowWidth - menuWidth - 5; if (top + menuHeight > windowHeight) top = windowHeight - menuHeight - 5; contextMenu.style.top = `${top}px`; contextMenu.style.left = `${left}px`; setTimeout(() => { const closeMenu = () => { if (contextMenu) contextMenu.remove(); document.removeEventListener('click', closeMenu); }; document.addEventListener('click', closeMenu, { once: true }); }, 0); }
function showReplyPreview(messageText, messageAuthor) { const container = DOMElements.userChat.replyContainer; container.style.display = 'block'; container.dataset.replyText = messageText; container.dataset.replyAuthor = messageAuthor; const previewText = messageText.length > 50 ? messageText.substring(0, 50) + '...' : messageText; container.innerHTML = `回覆: ${previewText} <span id="close-reply">×</span>`; container.querySelector('#close-reply').addEventListener('click', (e) => { e.stopPropagation(); hideReplyPreview(); }); }
function hideReplyPreview() { const container = DOMElements.userChat.replyContainer; container.style.display = 'none'; container.textContent = ''; container.dataset.replyText = ''; container.dataset.replyAuthor = ''; }
DOMElements.userChat.messagesContainer.addEventListener('click', (e) => { const thumbIcon = e.target.closest('.thumb-icon'); if (thumbIcon) { toggleThumb(thumbIcon); } });
function toggleThumb(element) { const messageElement = element.closest('.message'); const messageIndex = messageElement.dataset.index; chatSocket.send(JSON.stringify({ type: 'thumb_press', userName, index: messageIndex })); }
function updateThumbCount(messageIndex, thumbCount, likers) { const messageElement = document.querySelector(`.message[data-index="${messageIndex}"]`); if (!messageElement) return; const thumbCountElement = messageElement.querySelector('.thumb-count'); const thumbIcon = messageElement.querySelector('.thumb-icon'); if (thumbCountElement) thumbCountElement.textContent = thumbCount; if (thumbIcon && likers) { const hasLiked = likers.includes(userName); thumbIcon.classList.toggle('blue', hasLiked); thumbIcon.classList.toggle('gray', !hasLiked); } }
function markMessagesAsRead(notifiedPerson) { if (userName === notifiedPerson) { const ownMessages = document.querySelectorAll('.message.own'); ownMessages.forEach(msg => { const bundle = msg.querySelector('.message-bundle'); if (bundle && !bundle.querySelector('.read-status')) { const status = document.createElement('span'); status.className = 'read-status'; status.textContent = '已讀'; bundle.appendChild(status); } }); } }
function showTooltip(targetElement, text) { if (tooltipTimeout) clearTimeout(tooltipTimeout); if (tooltipElement) tooltipElement.remove(); tooltipElement = document.createElement('div'); tooltipElement.className = 'universal-tooltip'; tooltipElement.textContent = text; document.body.appendChild(tooltipElement); const targetRect = targetElement.getBoundingClientRect(); const tooltipRect = tooltipElement.getBoundingClientRect(); let top = targetRect.top - tooltipRect.height - 8; let left = targetRect.left + (targetRect.width / 2) - (tooltipRect.width / 2); if (top < 0) top = targetRect.bottom + 8; if (left < 0) left = 5; if (left + tooltipRect.width > window.innerWidth) left = window.innerWidth - tooltipRect.width - 5; tooltipElement.style.top = `${top + window.scrollY}px`; tooltipElement.style.left = `${left + window.scrollX}px`; tooltipElement.style.opacity = '1'; }
function hideTooltip() { if (tooltipElement) { tooltipElement.style.opacity = '0'; tooltipTimeout = setTimeout(() => { if (tooltipElement) { tooltipElement.remove(); tooltipElement = null; } }, 200); } }
function scrollToBottom(element) { if(element) element.scrollTop = element.scrollHeight; }
function handleGameOver(data) { const { winner, final_answer } = data; const congratulationsHTML = `<div class="system-announcement"><h3>🎉 恭喜！謎底已解開！ 🎉</h3><p>由玩家 <strong>${winner}</strong> 成功解開謎底！</p><h4>完整謎底：</h4><p>${final_answer.replace(/\n/g, '<br />')}</p></div>`; DOMElements.userChat.messagesContainer.innerHTML += congratulationsHTML; DOMElements.aiChat.messagesContainer.innerHTML += congratulationsHTML; DOMElements.userChat.messageBox.disabled = true; DOMElements.aiChat.messageBox.disabled = true; DOMElements.userChat.form.querySelector('button').disabled = true; DOMElements.aiChat.form.querySelector('button').disabled = true; scrollToBottom(DOMElements.userChat.messagesContainer); scrollToBottom(DOMElements.aiChat.messagesContainer); }