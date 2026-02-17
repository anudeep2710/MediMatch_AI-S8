// chatbot.js: Handles Gemini chatbot UI logic for PharmaSage

document.addEventListener('DOMContentLoaded', function () {
    const sendBtn = document.getElementById('chatbot-send-btn');
    const input = document.getElementById('chatbot-input');
    const chatBox = document.getElementById('chatbot-messages');
    const spinner = document.getElementById('chatbot-loading-spinner');
    const errorBox = document.getElementById('chatbot-error');
    let typingEl = null;

    function appendMessage(text, sender) {
        const msg = document.createElement('div');
        msg.className = 'chatbot-msg ' + (sender === 'user' ? 'user-msg' : 'bot-msg');
        const bubble = document.createElement('div');
        bubble.className = 'msg-bubble';
        bubble.textContent = text;
        msg.appendChild(bubble);
        chatBox.appendChild(msg);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    function showTyping() {
        if (typingEl) return;
        typingEl = document.createElement('div');
        typingEl.className = 'chatbot-msg bot-msg typing';
        const bubble = document.createElement('div');
        bubble.className = 'msg-bubble';
        // three animated dots
        for (let i = 0; i < 3; i++) {
            const dot = document.createElement('span');
            dot.className = 'typing-dot';
            bubble.appendChild(dot);
        }
        typingEl.appendChild(bubble);
        chatBox.appendChild(typingEl);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    function hideTyping() {
        if (typingEl && typingEl.parentNode) {
            typingEl.parentNode.removeChild(typingEl);
        }
        typingEl = null;
    }

    function setLoading(loading) {
        spinner.style.display = loading ? '' : 'none';
        sendBtn.disabled = loading;
        input.disabled = loading;
        if (loading) {
            showTyping();
        } else {
            hideTyping();
        }
    }

    sendBtn.addEventListener('click', function () {
        const question = input.value.trim();
        if (!question) return;
        errorBox.style.display = 'none';
        appendMessage(question, 'user');
        setLoading(true);
        fetch('/api/chatbot', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question })
        })
            .then(async res => {
                let data;
                try {
                    data = await res.json();
                } catch (e) {
                    console.error('Failed to parse JSON:', e, res);
                    errorBox.textContent = 'Invalid server response.';
                    errorBox.style.display = '';
                    setLoading(false);
                    return;
                }
                setLoading(false);
                if (res.ok && data.answer) {
                    appendMessage(data.answer, 'bot');
                } else {
                    console.error('API error:', data, res);
                    errorBox.textContent = data.error || 'Unknown error.';
                    errorBox.style.display = '';
                }
            })
            .catch(err => {
                setLoading(false);
                console.error('Fetch/network error:', err);
                errorBox.textContent = 'Network error.';
                errorBox.style.display = '';
            });
        input.value = '';
        input.focus();
    });

    input.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') {
            sendBtn.click();
        }
    });
});
