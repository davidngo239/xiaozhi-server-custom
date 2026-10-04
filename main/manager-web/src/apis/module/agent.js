import { getServiceUrl } from '../api';
import RequestService from '../httpRequest';

const CALLBACK_RETRY_LIMIT = 10;
const CALLBACK_RETRY_DELAY_MS = 2000;
const CALLBACK_RETRY_WINDOW_MS = CALLBACK_RETRY_LIMIT * CALLBACK_RETRY_DELAY_MS;

function retryCallbackRequest(retry, retryCount, onTerminalFailure, error, retryStartedAt) {
    if (!onTerminalFailure) {
        RequestService.reAjaxFun(() => retry(retryCount + 1))
        return
    }
    const startedAt = retryStartedAt || Date.now()
    if (retryCount >= CALLBACK_RETRY_LIMIT || Date.now() - startedAt >= CALLBACK_RETRY_WINDOW_MS) {
        RequestService.clearRequestTime()
        onTerminalFailure(error)
        return
    }
    setTimeout(() => retry(retryCount + 1, startedAt), CALLBACK_RETRY_DELAY_MS)
}

function attachTerminalFailure(request, onTerminalFailure) {
    if (onTerminalFailure) {
        request.fail((error) => {
            RequestService.clearRequestTime()
            onTerminalFailure(error)
        })
    }
    return request
}

function terminateCallbackRequest(onTerminalFailure, error) {
    RequestService.clearRequestTime()
    if (onTerminalFailure) {
        onTerminalFailure(error)
    }
}


export default {
    // Lấy danh sách đại lý
    getAgentList(callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/list`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail(() => {
                RequestService.reAjaxFun(() => {
                    this.getAgentList(callback);
                });
            }).send();
    },
    // Thêm đại lý
    addAgent(agentName, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent`)
            .method('POST')
            .data({ agentName: agentName })
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail(() => {
                RequestService.reAjaxFun(() => {
                    this.addAgent(agentName, callback);
                });
            }).send();
    },
    // Xóa đại lý
    deleteAgent(agentId, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/${agentId}`)
            .method('DELETE')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail(() => {
                RequestService.reAjaxFun(() => {
                    this.deleteAgent(agentId, callback);
                });
            }).send();
    },
    // Nhận cấu hình đại lý
    getDeviceConfig(agentId, callback, onTerminalFailure, retryCount = 0, retryStartedAt = 0) {
        const retryWindowStartedAt = retryStartedAt || Date.now()
        const request = RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/${agentId}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((err) => {
                console.error('获取配置失败:', err);
                retryCallbackRequest(
                    (nextRetryCount, nextRetryStartedAt) => this.getDeviceConfig(
                        agentId,
                        callback,
                        onTerminalFailure,
                        nextRetryCount,
                        nextRetryStartedAt
                    ),
                    retryCount,
                    onTerminalFailure,
                    err,
                    retryWindowStartedAt
                )
            })
        attachTerminalFailure(request, onTerminalFailure).send();
    },
    // Cấu hình đại lý
    updateAgentConfig(agentId, configData, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/${agentId}`)
            .method('PUT')
            .data(configData)
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail(() => {
                RequestService.reAjaxFun(() => {
                    this.updateAgentConfig(agentId, configData, callback);
                });
            }).send();
    },
    // Nhận danh sách ảnh chụp nhanh cấu hình tác nhân
    getAgentSnapshots(agentId, params, callback, onTerminalFailure, retryCount = 0, retryStartedAt = 0) {
        const retryWindowStartedAt = retryStartedAt || Date.now()
        const request = RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/${agentId}/snapshots`)
            .method('GET')
            .data(params)
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((error) => {
                retryCallbackRequest(
                    (nextRetryCount, nextRetryStartedAt) => this.getAgentSnapshots(
                        agentId,
                        params,
                        callback,
                        onTerminalFailure,
                        nextRetryCount,
                        nextRetryStartedAt
                    ),
                    retryCount,
                    onTerminalFailure,
                    error,
                    retryWindowStartedAt
                )
            })
        attachTerminalFailure(request, onTerminalFailure).send();
    },
    // Nhận thông tin chi tiết về ảnh chụp nhanh cấu hình đại lý
    getAgentSnapshot(agentId, snapshotId, callback, onTerminalFailure, retryCount = 0, retryStartedAt = 0) {
        const retryWindowStartedAt = retryStartedAt || Date.now()
        const request = RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/${agentId}/snapshots/${snapshotId}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((error) => {
                retryCallbackRequest(
                    (nextRetryCount, nextRetryStartedAt) => this.getAgentSnapshot(
                        agentId,
                        snapshotId,
                        callback,
                        onTerminalFailure,
                        nextRetryCount,
                        nextRetryStartedAt
                    ),
                    retryCount,
                    onTerminalFailure,
                    error,
                    retryWindowStartedAt
                )
            })
        attachTerminalFailure(request, onTerminalFailure).send();
    },
    // Khôi phục ảnh chụp nhanh cấu hình tác nhân
    restoreAgentSnapshot(agentId, snapshotId, currentStateToken, callback, onTerminalFailure) {
        const request = RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/${agentId}/snapshots/${snapshotId}/restore`)
            .method('POST')
            .data({ currentStateToken })
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((error) => {
                terminateCallbackRequest(onTerminalFailure, error)
            })
        attachTerminalFailure(request, onTerminalFailure).send();
    },
    // Xóa ảnh chụp nhanh cấu hình đại lý
    deleteAgentSnapshot(agentId, snapshotId, callback, onTerminalFailure) {
        const request = RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/${agentId}/snapshots/${snapshotId}`)
            .method('DELETE')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((error) => {
                terminateCallbackRequest(onTerminalFailure, error)
            })
        attachTerminalFailure(request, onTerminalFailure).send();
    },
    // Phương pháp mới: Lấy mẫu đại lý
    getAgentTemplate(callback) {  // Xóa tham số templateName
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/template`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((err) => {
                console.error('获取模板失败:', err);
                RequestService.reAjaxFun(() => {
                    this.getAgentTemplate(callback);
                });
            }).send();
    },

    // Mới: Nhận danh sách mẫu đại lý được phân trang
    getAgentTemplatesPage(params, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/template/page`)
            .method('GET')
            .data(params)
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((err) => {
                console.error('获取模板分页列表失败:', err);
                RequestService.reAjaxFun(() => {
                    this.getAgentTemplatesPage(params, callback);
                });
            }).send();
    },
    // Lấy danh sách phiên đại lý
    getAgentSessions(agentId, params, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/${agentId}/sessions`)
            .method('GET')
            .data(params)
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail(() => {
                RequestService.reAjaxFun(() => {
                    this.getAgentSessions(agentId, params, callback);
                });
            }).send();
    },
    // Nhận lịch sử trò chuyện của đại lý
    getAgentChatHistory(agentId, sessionId, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/${agentId}/chat-history/${sessionId}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail(() => {
                RequestService.reAjaxFun(() => {
                    this.getAgentChatHistory(agentId, sessionId, callback);
                });
            }).send();
    },
    // Nhận ID tải xuống âm thanh
    getAudioId(audioId, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/audio/${audioId}`)
            .method('POST')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail(() => {
                RequestService.reAjaxFun(() => {
                    this.getAudioId(audioId, callback);
                });
            }).send();
    },
    // Lấy địa chỉ điểm truy cập MCP của đại lý
    getAgentMcpAccessAddress(agentId, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/mcp/address/${agentId}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .fail((err) => {
                callback(err);
            })
            .networkFail(() => {
                RequestService.reAjaxFun(() => {
                    this.getAgentMcpAccessAddress(agentId, callback);
                });
            }).send();
    },
    // Lấy danh sách công cụ MCP cho đại lý
    getAgentMcpToolsList(agentId, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/mcp/tools/${agentId}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail(() => {
                RequestService.reAjaxFun(() => {
                    this.getAgentMcpToolsList(agentId, callback);
                });
            }).send();
    },
    // Thêm giọng nói của đại lý
    addAgentVoicePrint(voicePrintData, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/voice-print`)
            .method('POST')
            .data(voicePrintData)
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail(() => {
                RequestService.reAjaxFun(() => {
                    this.addAgentVoicePrint(voicePrintData, callback);
                });
            }).send();
    },
    // Lấy danh sách giọng nói của đại lý được chỉ định
    getAgentVoicePrintList(id, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/voice-print/list/${id}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail(() => {
                RequestService.reAjaxFun(() => {
                    this.getAgentVoicePrintList(id, callback);
                });
            }).send();
    },
    // Xóa giọng nói của đại lý
    deleteAgentVoicePrint(id, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/voice-print/${id}`)
            .method('DELETE')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail(() => {
                RequestService.reAjaxFun(() => {
                    this.deleteAgentVoicePrint(id, callback);
                });
            }).send();
    },
    // Cập nhật giọng nói của nhân viên
    updateAgentVoicePrint(voicePrintData, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/voice-print`)
            .method('PUT')
            .data(voicePrintData)
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail(() => {
                RequestService.reAjaxFun(() => {
                    this.updateAgentVoicePrint(voicePrintData, callback);
                });
            }).send();
    },
    // Nhận lịch sử trò chuyện của loại người dùng đại lý được chỉ định
    getRecentlyFiftyByAgentId(id, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/${id}/chat-history/user`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail(() => {
                RequestService.reAjaxFun(() => {
                    this.getRecentlyFiftyByAgentId(id, callback);
                });
            }).send();
    },
    // Nhận lịch sử trò chuyện của loại người dùng đại lý được chỉ định
    getContentByAudioId(id, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/${id}/chat-history/audio`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail(() => {
                RequestService.reAjaxFun(() => {
                    this.getContentByAudioId(id, callback);
                });
            }).send();
    },
    // Thêm phương thức sau vào cuối tệp (sau phương thức cuối cùng và trước dấu ngoặc nhọn):
    // Thêm mẫu đại lý mới
    addAgentTemplate(templateData, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/template`)
            .method('POST')
            .data(templateData)
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail(() => {
                RequestService.reAjaxFun(() => {
                    this.addAgentTemplate(templateData, callback);
                });
            }).send();
    },

    // Cập nhật mẫu đại lý
    updateAgentTemplate(templateData, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/template`)
            .method('PUT')
            .data(templateData)
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail(() => {
                RequestService.reAjaxFun(() => {
                    this.updateAgentTemplate(templateData, callback);
                });
            }).send();
    },

    // Xóa mẫu đại lý
    deleteAgentTemplate(id, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/template/${id}`)
            .method('DELETE')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail(() => {
                RequestService.reAjaxFun(() => {
                    this.deleteAgentTemplate(id, callback);
                });
            }).send();
    },

    // Xóa mẫu đại lý theo đợt
    batchDeleteAgentTemplate(ids, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/template/batch-remove`) // Thay đổi sang URL mới
            .method('POST')
            .data(Array.isArray(ids) ? ids : [ids]) // Đảm bảo nó ở định dạng mảng
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail(() => {
                RequestService.reAjaxFun(() => {
                    this.batchDeleteAgentTemplate(ids, callback);
                });
            }).send();
    },
    // Thêm một phương thức để lấy một mẫu sau phương thức getAgentTemplate
    getAgentTemplateById(templateId, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/template/${templateId}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((err) => {
                console.error('获取单个模板失败:', err);
                RequestService.reAjaxFun(() => {
                    this.getAgentTemplateById(templateId, callback);
                });
            }).send();
    },

    // Nhận liên kết tải xuống lịch sử trò chuyện UUID
    getDownloadUrl(agentId, sessionId, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/chat-history/getDownloadUrl/${agentId}/${sessionId}`)
            .method('POST')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail(() => {
                RequestService.reAjaxFun(() => {
                    this.getDownloadUrl(agentId, sessionId, callback);
                });
            }).send();
    },
    
    // Đại lý tìm kiếm
    searchAgent(keyword, searchType, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/list?keyword=${encodeURIComponent(keyword)}&searchType=${searchType}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail(() => {
                RequestService.reAjaxFun(() => {
                    this.searchAgent(keyword, searchType, callback);
                });
            }).send();
    },
    // Nhận thẻ đại lý
    getAgentTags(agentId, callback, onTerminalFailure, retryCount = 0, retryStartedAt = 0) {
        const retryWindowStartedAt = retryStartedAt || Date.now()
        const request = RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/${agentId}/tags`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((error) => {
                retryCallbackRequest(
                    (nextRetryCount, nextRetryStartedAt) => this.getAgentTags(
                        agentId,
                        callback,
                        onTerminalFailure,
                        nextRetryCount,
                        nextRetryStartedAt
                    ),
                    retryCount,
                    onTerminalFailure,
                    error,
                    retryWindowStartedAt
                )
            })
        attachTerminalFailure(request, onTerminalFailure).send();
    },
    // Lưu nhãn đại lý
    saveAgentTags(agentId, tags, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/agent/${agentId}/tags`)
            .method('PUT')
            .data(tags)
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail(() => {
                RequestService.reAjaxFun(() => {
                    this.saveAgentTags(agentId, tags, callback);
                });
            }).send();
    },
}
