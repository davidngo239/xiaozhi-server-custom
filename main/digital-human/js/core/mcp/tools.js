import { log } from '../../utils/logger.js?v=0205';

// ==========================================
// Logic quản lý công cụ MCP
// ==========================================

// biến toàn cục
let mcpTools = [];
let mcpEditingIndex = null;
let mcpProperties = [];
let websocket = null; // Sẽ được thiết lập từ bên ngoài

/**
 * Thiết lập phiên WebSocket
 * @param {WebSocket} ws - Phiên kết nối WebSocket
 */
export function setWebSocket(ws) {
    websocket = ws;
}

/**
 * Khởi tạo công cụ MCP
 */
export async function initMcpTools() {
    // Tải dữ liệu công cụ mặc định
    const defaultMcpTools = await fetch("js/config/default-mcp-tools.json").then(res => res.json());
    const savedTools = localStorage.getItem('mcpTools');
    if (savedTools) {
        try {
            const parsedTools = JSON.parse(savedTools);
            // Gộp công cụ mặc định với công cụ đã lưu, giữ lại công cụ tùy chỉnh
            const defaultToolNames = new Set(defaultMcpTools.map(t => t.name));
            // Thêm các công cụ chưa có trong danh sách mặc định
            parsedTools.forEach(tool => {
                if (!defaultToolNames.has(tool.name)) {
                    defaultMcpTools.push(tool);
                }
            });
            mcpTools = defaultMcpTools;
        } catch (e) {
            log('Không tải được công cụ MCP; dùng công cụ mặc định', 'warning');
            mcpTools = [...defaultMcpTools];
        }
    } else {
        mcpTools = [...defaultMcpTools];
    }
    renderMcpTools();
    setupMcpEventListeners();
}

/**
 * Hiển thị danh sách công cụ
 */
function renderMcpTools() {
    const container = document.getElementById('mcpToolsContainer');
    const countSpan = document.getElementById('mcpToolsCount');
    if (!container) {
        return; // Container not found, skip rendering
    }
    if (countSpan) {
        countSpan.textContent = `${mcpTools.length} công cụ`;
    }
    if (mcpTools.length === 0) {
        container.innerHTML = '<div style="text-align: center; padding: 30px; color: #999;">Chưa có công cụ. Nhấn nút phía dưới để thêm công cụ mới</div>';
        return;
    }
    container.innerHTML = mcpTools.map((tool, index) => {
        const paramCount = tool.inputSchema.properties ? Object.keys(tool.inputSchema.properties).length : 0;
        const requiredCount = tool.inputSchema.required ? tool.inputSchema.required.length : 0;
        const hasMockResponse = tool.mockResponse && Object.keys(tool.mockResponse).length > 0;
        return `
            <div class="mcp-tool-card">
                <div class="mcp-tool-header">
                    <div class="mcp-tool-name">${tool.name}</div>
                    <div class="mcp-tool-actions">
                        <button class="mcp-edit-btn" onclick="window.mcpModule.editMcpTool(${index})">
                            ✏️ Sửa
                        </button>
                        <button class="mcp-delete-btn" onclick="window.mcpModule.deleteMcpTool(${index})">
                            🗑️ Xóa
                        </button>
                    </div>
                </div>
                <div class="mcp-tool-description">${tool.description}</div>
                <div class="mcp-tool-info">
                    <div class="mcp-tool-info-row">
                        <span class="mcp-tool-info-label">Số tham số:</span>
                        <span class="mcp-tool-info-value">${paramCount} tham số ${requiredCount > 0 ? `(${requiredCount} tham số bắt buộc)` : ''}</span>
                    </div>
                    <div class="mcp-tool-info-row">
                        <span class="mcp-tool-info-label">Kết quả mô phỏng:</span>
                        <span class="mcp-tool-info-value">${hasMockResponse ? '✅ Đã cấu hình: ' + JSON.stringify(tool.mockResponse) : '⚪ Dùng mặc định'}</span>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

/**
 * Hiển thị danh sách tham số
 */
function renderMcpProperties() {
    const container = document.getElementById('mcpPropertiesContainer');
    const emptyState = document.getElementById('mcpEmptyState');
    if (!container) {
        return; // Container not found, skip rendering
    }
    if (mcpProperties.length === 0) {
        if (emptyState) {
            emptyState.style.display = 'block';
        }
        container.innerHTML = '';
        return;
    }
    if (emptyState) {
        emptyState.style.display = 'none';
    }
    container.innerHTML = mcpProperties.map((prop, index) => `
        <div class="mcp-property-card" onclick="window.mcpModule.editMcpProperty(${index})">
            <div class="mcp-property-row-label">
                <span class="mcp-property-label">Tên tham số</span>
                <span class="mcp-property-value">${prop.name}${prop.required ? ' <span class="mcp-property-required-badge">[Bắt buộc]</span>' : ''}</span>
            </div>
            <div class="mcp-property-row-label">
                <span class="mcp-property-label">Kiểu dữ liệu</span>
                <span class="mcp-property-value">${getTypeLabel(prop.type)}</span>
            </div>
            <div class="mcp-property-row-label">
                <span class="mcp-property-label">Mô tả</span>
                <span class="mcp-property-value">${prop.description || '-'}</span>
            </div>
            <div class="mcp-property-row-action">
                <button class="mcp-property-delete-btn" onclick="event.stopPropagation(); window.mcpModule.deleteMcpProperty(${index})">Xóa</button>
            </div>
        </div>
    `).join('');
}

/**
 * Lấy nhãn kiểu dữ liệu
 */
function getTypeLabel(type) {
    const typeMap = {
        'string': 'Chuỗi',
        'integer': 'Số nguyên',
        'number': 'Số',
        'boolean': 'Boolean',
        'array': 'Mảng',
        'object': 'Đối tượng'
    };
    return typeMap[type] || type;
}

/**
 * Thêm tham số và mở hộp thoại chỉnh sửa
 */
function addMcpProperty() {
    openPropertyModal();
}

/**
 * Chỉnh sửa tham số và mở hộp thoại
 */
function editMcpProperty(index) {
    openPropertyModal(index);
}

/**
 * Mở hộp thoại chỉnh sửa tham số
 */
function openPropertyModal(index = null) {
    const form = document.getElementById('mcpPropertyForm');
    const title = document.getElementById('mcpPropertyModalTitle');
    document.getElementById('mcpPropertyIndex').value = index !== null ? index : -1;

    if (index !== null) {
        const prop = mcpProperties[index];
        title.textContent = 'Sửa tham số';
        document.getElementById('mcpPropertyName').value = prop.name;
        document.getElementById('mcpPropertyType').value = prop.type || 'string';
        document.getElementById('mcpPropertyMinimum').value = prop.minimum !== undefined ? prop.minimum : '';
        document.getElementById('mcpPropertyMaximum').value = prop.maximum !== undefined ? prop.maximum : '';
        document.getElementById('mcpPropertyDescription').value = prop.description || '';
        document.getElementById('mcpPropertyRequired').checked = prop.required || false;
    } else {
        title.textContent = 'Thêm tham số';
        form.reset();
        document.getElementById('mcpPropertyName').value = `param_${mcpProperties.length + 1}`;
        document.getElementById('mcpPropertyType').value = 'string';
        document.getElementById('mcpPropertyMinimum').value = '';
        document.getElementById('mcpPropertyMaximum').value = '';
        document.getElementById('mcpPropertyDescription').value = '';
        document.getElementById('mcpPropertyRequired').checked = false;
    }

    updatePropertyRangeVisibility();
    document.getElementById('mcpPropertyModal').style.display = 'flex';
}

/**
 * Đóng hộp thoại chỉnh sửa tham số
 */
function closePropertyModal() {
    document.getElementById('mcpPropertyModal').style.display = 'none';
}

/**
 * Cập nhật trạng thái hiển thị của trường khoảng giá trị
 */
function updatePropertyRangeVisibility() {
    const type = document.getElementById('mcpPropertyType').value;
    const rangeGroup = document.getElementById('mcpPropertyRangeGroup');
    if (type === 'integer' || type === 'number') {
        rangeGroup.style.display = 'block';
    } else {
        rangeGroup.style.display = 'none';
    }
}

/**
 * Xử lý việc gửi biểu mẫu tham số
 */
function handlePropertySubmit(e) {
    e.preventDefault();
    const index = parseInt(document.getElementById('mcpPropertyIndex').value);
    const name = document.getElementById('mcpPropertyName').value.trim();
    const type = document.getElementById('mcpPropertyType').value;
    const minimum = document.getElementById('mcpPropertyMinimum').value;
    const maximum = document.getElementById('mcpPropertyMaximum').value;
    const description = document.getElementById('mcpPropertyDescription').value.trim();
    const required = document.getElementById('mcpPropertyRequired').checked;

    // Kiểm tra trùng lặp tên
    const isDuplicate = mcpProperties.some((p, i) => i !== index && p.name === name);
    if (isDuplicate) {
        alert('Tên tham số đã tồn tại. Vui lòng dùng tên khác');
        return;
    }

    const propData = {
        name,
        type,
        description,
        required
    };

    // Thêm giới hạn phạm vi cho các loại số
    if (type === 'integer' || type === 'number') {
        if (minimum !== '') {
            propData.minimum = parseFloat(minimum);
        }
        if (maximum !== '') {
            propData.maximum = parseFloat(maximum);
        }
    }

    if (index >= 0) {
        mcpProperties[index] = propData;
    } else {
        mcpProperties.push(propData);
    }

    renderMcpProperties();
    closePropertyModal();
}

/**
 * Xóa tham số
 */
function deleteMcpProperty(index) {
    mcpProperties.splice(index, 1);
    renderMcpProperties();
}

/**
 * Thiết lập bộ lắng nghe sự kiện
 */
function setupMcpEventListeners() {
    const panel = document.getElementById('mcpToolsPanel');
    const addBtn = document.getElementById('addMcpToolBtn');
    const modal = document.getElementById('mcpToolModal');
    const closeBtn = document.getElementById('closeMcpModalBtn');
    const cancelBtn = document.getElementById('cancelMcpBtn');
    const form = document.getElementById('mcpToolForm');
    const addPropertyBtn = document.getElementById('addMcpPropertyBtn');

    // Các phần tử của hộp thoại chỉnh sửa tham số
    const propertyModal = document.getElementById('mcpPropertyModal');
    const closePropertyBtn = document.getElementById('closeMcpPropertyModalBtn');
    const cancelPropertyBtn = document.getElementById('cancelMcpPropertyBtn');
    const propertyForm = document.getElementById('mcpPropertyForm');
    const propertyTypeSelect = document.getElementById('mcpPropertyType');

    // Quay lại sớm nếu các yếu tố bắt buộc không tồn tại (ví dụ: trong môi trường thử nghiệm)
    if (!panel || !addBtn || !modal || !closeBtn || !cancelBtn || !form || !addPropertyBtn) {
        return;
    }
    addBtn.addEventListener('click', () => openMcpModal());
    closeBtn.addEventListener('click', closeMcpModal);
    cancelBtn.addEventListener('click', closeMcpModal);
    addPropertyBtn.addEventListener('click', addMcpProperty);
    form.addEventListener('submit', handleMcpSubmit);

    // Sự kiện của hộp thoại chỉnh sửa tham số
    if (propertyModal && closePropertyBtn && cancelPropertyBtn && propertyForm && propertyTypeSelect) {
        closePropertyBtn.addEventListener('click', closePropertyModal);
        cancelPropertyBtn.addEventListener('click', closePropertyModal);
        propertyForm.addEventListener('submit', handlePropertySubmit);
        propertyTypeSelect.addEventListener('change', updatePropertyRangeVisibility);
    }
}

/**
 * Mở hộp phương thức
 */
function openMcpModal(index = null) {
    const isConnected = websocket && websocket.readyState === WebSocket.OPEN;
    if (isConnected) {
        alert('WebSocket đang kết nối, không thể sửa công cụ');
        return;
    }
    mcpEditingIndex = index;
    const errorContainer = document.getElementById('mcpErrorContainer');
    errorContainer.innerHTML = '';
    if (index !== null) {
        document.getElementById('mcpModalTitle').textContent = 'Sửa công cụ';
        const tool = mcpTools[index];
        document.getElementById('mcpToolName').value = tool.name;
        document.getElementById('mcpToolDescription').value = tool.description;
        document.getElementById('mcpMockResponse').value = tool.mockResponse ? JSON.stringify(tool.mockResponse, null, 2) : '';
        mcpProperties = [];
        const schema = tool.inputSchema;
        if (schema.properties) {
            Object.keys(schema.properties).forEach(key => {
                const prop = schema.properties[key];
                mcpProperties.push({
                    name: key,
                    type: prop.type || 'string',
                    minimum: prop.minimum,
                    maximum: prop.maximum,
                    description: prop.description || '',
                    required: schema.required && schema.required.includes(key)
                });
            });
        }
    } else {
        document.getElementById('mcpModalTitle').textContent = 'Thêm công cụ';
        document.getElementById('mcpToolForm').reset();
        mcpProperties = [];
    }
    renderMcpProperties();
    document.getElementById('mcpToolModal').style.display = 'flex';
}

/**
 * Đóng hộp thoại
 */
function closeMcpModal() {
    document.getElementById('mcpToolModal').style.display = 'none';
    mcpEditingIndex = null;
    document.getElementById('mcpToolForm').reset();
    mcpProperties = [];
    document.getElementById('mcpErrorContainer').innerHTML = '';
}

/**
 * Xử lý việc gửi biểu mẫu
 */
function handleMcpSubmit(e) {
    e.preventDefault();
    const errorContainer = document.getElementById('mcpErrorContainer');
    errorContainer.innerHTML = '';
    const name = document.getElementById('mcpToolName').value.trim();
    const description = document.getElementById('mcpToolDescription').value.trim();
    const mockResponseText = document.getElementById('mcpMockResponse').value.trim();
    // Kiểm tra trùng lặp tên
    const isDuplicate = mcpTools.some((tool, index) => tool.name === name && index !== mcpEditingIndex);
    if (isDuplicate) {
        showMcpError('Tên công cụ đã tồn tại. Vui lòng dùng tên khác');
        return;
    }
    // Phân tích kết quả trả về mô phỏng
    let mockResponse = null;
    if (mockResponseText) {
        try {
            mockResponse = JSON.parse(mockResponseText);
        } catch (e) {
            showMcpError('Kết quả mô phỏng không phải JSON hợp lệ: ' + e.message);
            return;
        }
    }
    // Xây dựng lược đồ đầu vào
    const inputSchema = { type: "object", properties: {}, required: [] };
    mcpProperties.forEach(prop => {
        const propSchema = { type: prop.type };
        if (prop.description) {
            propSchema.description = prop.description;
        }
        if ((prop.type === 'integer' || prop.type === 'number')) {
            if (prop.minimum !== undefined && prop.minimum !== '') {
                propSchema.minimum = prop.minimum;
            }
            if (prop.maximum !== undefined && prop.maximum !== '') {
                propSchema.maximum = prop.maximum;
            }
        }
        inputSchema.properties[prop.name] = propSchema;
        if (prop.required) {
            inputSchema.required.push(prop.name);
        }
    });
    if (inputSchema.required.length === 0) {
        delete inputSchema.required;
    }
    const tool = { name, description, inputSchema, mockResponse };
    if (mcpEditingIndex !== null) {
        mcpTools[mcpEditingIndex] = tool;
        log(`Đã cập nhật công cụ: ${name}`, 'success');
    } else {
        mcpTools.push(tool);
        log(`Đã Thêm công cụ: ${name}`, 'success');
    }
    saveMcpTools();
    renderMcpTools();
    closeMcpModal();
}

/**
 * Hiển thị lỗi
 */
function showMcpError(message) {
    const errorContainer = document.getElementById('mcpErrorContainer');
    errorContainer.innerHTML = `<div class="mcp-error">${message}</div>`;
}

/**
 * Sửa công cụ
 */
function editMcpTool(index) {
    openMcpModal(index);
}

/**
 * Xóa công cụ
 */
function deleteMcpTool(index) {
    const isConnected = websocket && websocket.readyState === WebSocket.OPEN;
    if (isConnected) {
        alert('WebSocket đang kết nối, không thể sửa công cụ');
        return;
    }
    if (confirm(`Bạn có muốn xóa công cụ "${mcpTools[index].name}" không?`)) {
        const toolName = mcpTools[index].name;
        mcpTools.splice(index, 1);
        saveMcpTools();
        renderMcpTools();
        log(`Đã Xóacông cụ: ${toolName}`, 'info');
    }
}

/**
 * Lưu công cụ
 */
function saveMcpTools() {
    localStorage.setItem('mcpTools', JSON.stringify(mcpTools));
}

/**
 * Lấy danh sách các công cụ
 */
export function getMcpTools() {
    return mcpTools.map(tool => ({ name: tool.name, description: tool.description, inputSchema: tool.inputSchema }));
}

/**
 * Thực hiện lệnh gọi công cụ
 */
export async function executeMcpTool(toolName, toolArgs) {
    const tool = mcpTools.find(t => t.name === toolName);
    if (!tool) {
        log(`không tìm thấycông cụ: ${toolName}`, 'error');
        return { success: false, error: `Công cụ không xác định: ${toolName}` };
    }

    // Xử lý các công cụ ảnh
    if (toolName === 'self_camera_take_photo') {
        if (typeof window.takePhoto === 'function') {
            const question = toolArgs && toolArgs.question ? toolArgs.question : 'Mô tả những vật thể bạn nhìn thấy';
            log(`Đang chụp ảnh theo yêu cầu: ${question}`, 'info');
            const result = await window.takePhoto(question);
            return result;
        } else {
            log('Tính năng chụp ảnh không khả dụng', 'warning');
            return { success: false, error: 'Camera chưa bật hoặc không hỗ trợ chụp ảnh' };
        }
    }

    // Nếu có kết quả trả về giả, hãy sử dụng nó
    if (tool.mockResponse) {
        // Thay thế các biến mẫu
        let responseStr = JSON.stringify(tool.mockResponse);
        // Thay thế các biến ở định dạng ${paramName}
        if (toolArgs) {
            Object.keys(toolArgs).forEach(key => {
                const regex = new RegExp(`\\$\\{${key}\\}`, 'g');
                responseStr = responseStr.replace(regex, toolArgs[key]);
            });
        }
        try {
            const response = JSON.parse(responseStr);
            log(`Công cụ ${toolName} đã thực hiện thành công，trả vềkết quả mô phỏng: ${responseStr}`, 'success');
            return response;
        } catch (e) {
            log(`Phân tích kết quả mô phỏng thất bại: ${e.message}`, 'error');
            return tool.mockResponse;
        }
    }
    // Không có kết quả trả về mô phỏng và thông báo thành công mặc định được trả về.
    log(`Công cụ ${toolName} đã chạy thành công, trả về kết quả mặc định`, 'success');
    return { success: true, message: `Công cụ ${toolName} đã thực hiện thành công`, tool: toolName, arguments: toolArgs };
}

// Hiển thị các phương thức toàn cục được gọi bởi các sự kiện nội tuyến HTML
window.mcpModule = { addMcpProperty, editMcpProperty, deleteMcpProperty, editMcpTool, deleteMcpTool };
