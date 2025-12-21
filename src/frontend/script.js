// Configuration
const API_BASE_URL = window.location.hostname === 'localhost'
    ? 'http://localhost:8000'
    : 'http://localhost:8000'; // Update this for production

// DOM Elements
const chatHistory = document.getElementById('chatHistory');
const userInput = document.getElementById('userInput');
const sendButton = document.getElementById('sendButton');
const buttonText = document.getElementById('buttonText');
const buttonLoader = document.getElementById('buttonLoader');
const charCount = document.getElementById('charCount');
const chatForm = document.getElementById('chatForm');
const apiStatus = document.getElementById('apiStatus');

// State
let isLoading = false;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Character counter
    userInput.addEventListener('input', () => {
        const count = userInput.value.length;
        charCount.textContent = count;

        if (count > 450) {
            charCount.style.color = 'var(--error-color)';
        } else {
            charCount.style.color = 'var(--text-secondary)';
        }
    });

    // Check API status
    checkAPIStatus();

    // Focus input
    userInput.focus();
});

// Check API status
async function checkAPIStatus() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/health`);
        if (response.ok) {
            apiStatus.className = 'api-status online';
            apiStatus.textContent = 'API Connected';
            setTimeout(() => {
                apiStatus.style.display = 'none';
            }, 3000);
        } else {
            apiStatus.className = 'api-status offline';
            apiStatus.textContent = 'API Offline';
        }
    } catch (error) {
        apiStatus.className = 'api-status offline';
        apiStatus.textContent = 'API Unreachable';
    }
}

// Use example question
function useExample(element) {
    userInput.value = element.textContent;
    userInput.focus();
    charCount.textContent = element.textContent.length;
}

// Send message
async function sendMessage(event) {
    event.preventDefault();

    if (isLoading) return;

    const message = userInput.value.trim();
    if (!message) return;

    // Clear welcome message if it exists
    const welcomeMsg = chatHistory.querySelector('.welcome-message');
    if (welcomeMsg) {
        welcomeMsg.remove();
    }

    // Add user message
    addUserMessage(message);

    // Clear input
    userInput.value = '';
    charCount.textContent = '0';

    // Set loading state
    setLoading(true);

    try {
        // Call API
        const response = await fetch(`${API_BASE_URL}/api/chat/ask`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                include_explanation: true,
                include_visualizations: true,
                max_attempts: 3
            })
        });

        const data = await response.json();

        if (data.success) {
            addAssistantMessage(data);
        } else {
            addErrorMessage(data.error || 'An error occurred');
        }

    } catch (error) {
        console.error('Error:', error);
        addErrorMessage('Failed to connect to the API. Please check if the server is running.');
    } finally {
        setLoading(false);
    }
}

// Add user message to chat
function addUserMessage(text) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message user';
    messageDiv.innerHTML = `
        <div class="message-header">You</div>
        <div class="message-content">${escapeHtml(text)}</div>
    `;
    chatHistory.appendChild(messageDiv);
    scrollToBottom();
}

// Add assistant message to chat
function addAssistantMessage(data) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';

    let content = '<div class="message-header">AI Assistant</div>';

    // SQL Section
    if (data.sql) {
        content += `
            <div class="sql-section">
                <div class="sql-header" onclick="toggleSQLSection(this)">
                    <span>Generated SQL Query</span>
                    <button class="copy-button" onclick="copySQL(event, this)">Copy</button>
                </div>
                <div class="sql-code">${escapeHtml(data.sql)}</div>
            </div>
        `;
    }

    // Metadata
    if (data.confidence || data.execution_time) {
        content += '<div class="metadata">';

        if (data.confidence) {
            const confidenceClass = data.confidence >= 0.8 ? 'confidence-high' :
                                  data.confidence >= 0.6 ? 'confidence-medium' :
                                  'confidence-low';
            content += `
                <div class="metadata-item">
                    <span class="metadata-label">Confidence:</span>
                    <span class="metadata-value ${confidenceClass}">
                        ${(data.confidence * 100).toFixed(0)}%
                    </span>
                </div>
            `;
        }

        if (data.execution_time) {
            content += `
                <div class="metadata-item">
                    <span class="metadata-label">Execution Time:</span>
                    <span class="metadata-value">${data.execution_time.toFixed(2)}s</span>
                </div>
            `;
        }

        if (data.results && data.results.row_count !== undefined) {
            content += `
                <div class="metadata-item">
                    <span class="metadata-label">Rows:</span>
                    <span class="metadata-value">${data.results.row_count}</span>
                </div>
            `;
        }

        content += '</div>';
    }

    // Results Table
    if (data.results && data.results.data && data.results.data.length > 0) {
        content += '<div class="results-table-wrapper">';
        content += '<table class="results-table">';

        // Headers
        content += '<thead><tr>';
        data.results.columns.forEach(col => {
            content += `<th>${escapeHtml(col)}</th>`;
        });
        content += '</tr></thead>';

        // Rows (limit to first 50 for display)
        content += '<tbody>';
        const displayRows = data.results.data.slice(0, 50);
        displayRows.forEach(row => {
            content += '<tr>';
            data.results.columns.forEach(col => {
                const value = row[col];
                content += `<td>${escapeHtml(formatValue(value))}</td>`;
            });
            content += '</tr>';
        });
        content += '</tbody></table>';

        if (data.results.data.length > 50) {
            content += `<div style="padding: 8px; text-align: center; color: var(--text-secondary); font-size: 0.85rem;">Showing first 50 of ${data.results.data.length} rows</div>`;
        }

        content += '</div>';
    }

    // Insights
    if (data.insights) {
        content += '<div class="insights-section">';

        if (data.insights.summary) {
            content += `<h4>Summary</h4><p>${escapeHtml(data.insights.summary)}</p>`;
        }

        if (data.insights.key_insights && data.insights.key_insights.length > 0) {
            content += '<h4>Key Insights</h4><ul>';
            data.insights.key_insights.forEach(insight => {
                content += `<li>${escapeHtml(insight)}</li>`;
            });
            content += '</ul>';
        }

        if (data.insights.detailed_analysis) {
            content += `<div class="detailed-analysis">${escapeHtml(data.insights.detailed_analysis)}</div>`;
        }

        if (data.insights.follow_up_questions && data.insights.follow_up_questions.length > 0) {
            content += '<h4 style="margin-top: 12px;">Suggested Follow-up Questions</h4><ul>';
            data.insights.follow_up_questions.forEach(question => {
                content += `<li style="cursor: pointer; color: var(--primary-color);" onclick="useFollowUpQuestion(this)">${escapeHtml(question)}</li>`;
            });
            content += '</ul>';
        }

        content += '</div>';
    }

    messageDiv.innerHTML = content;
    chatHistory.appendChild(messageDiv);
    scrollToBottom();
}

// Add error message to chat
function addErrorMessage(error) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message error';
    messageDiv.innerHTML = `
        <div class="message-header">Error</div>
        <div class="message-content">${escapeHtml(error)}</div>
    `;
    chatHistory.appendChild(messageDiv);
    scrollToBottom();
}

// Toggle SQL section
function toggleSQLSection(header) {
    const codeDiv = header.nextElementSibling;
    if (codeDiv.style.display === 'none') {
        codeDiv.style.display = 'block';
    } else {
        codeDiv.style.display = 'none';
    }
}

// Copy SQL to clipboard
async function copySQL(event, button) {
    event.stopPropagation();
    const sqlCode = button.closest('.sql-section').querySelector('.sql-code').textContent;

    try {
        await navigator.clipboard.writeText(sqlCode);
        const originalText = button.textContent;
        button.textContent = 'Copied!';
        setTimeout(() => {
            button.textContent = originalText;
        }, 2000);
    } catch (error) {
        console.error('Failed to copy:', error);
    }
}

// Use follow-up question
function useFollowUpQuestion(element) {
    userInput.value = element.textContent;
    userInput.focus();
    charCount.textContent = element.textContent.length;
    // Optionally auto-submit
    // chatForm.dispatchEvent(new Event('submit'));
}

// Set loading state
function setLoading(loading) {
    isLoading = loading;
    sendButton.disabled = loading;
    userInput.disabled = loading;

    if (loading) {
        buttonText.style.display = 'none';
        buttonLoader.style.display = 'inline-block';
    } else {
        buttonText.style.display = 'inline';
        buttonLoader.style.display = 'none';
    }
}

// Scroll to bottom of chat
function scrollToBottom() {
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Format value for display
function formatValue(value) {
    if (value === null || value === undefined) return '';
    if (typeof value === 'number') {
        // Format large numbers with commas
        if (Math.abs(value) >= 1000) {
            return value.toLocaleString();
        }
        // Format decimals to 2 places
        if (value % 1 !== 0) {
            return value.toFixed(2);
        }
    }
    return String(value);
}

// Handle Enter key (Shift+Enter for new line, Enter to submit)
userInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        chatForm.dispatchEvent(new Event('submit'));
    }
});
