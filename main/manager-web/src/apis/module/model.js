import { getServiceUrl } from '../api';
import RequestService from '../httpRequest';

const CALLBACK_RETRY_LIMIT = 10;
const CALLBACK_RETRY_DELAY_MS = 2000;
const CALLBACK_RETRY_WINDOW_MS = CALLBACK_RETRY_LIMIT * CALLBACK_RETRY_DELAY_MS;

function retryCallbackRequest(retry, retryCount, onTerminalFailure, error, retryStartedAt) {
  if (!onTerminalFailure) {
    RequestService.reAjaxFun(() => retry(retryCount + 1));
    return;
  }
  const startedAt = retryStartedAt || Date.now();
  if (retryCount >= CALLBACK_RETRY_LIMIT || Date.now() - startedAt >= CALLBACK_RETRY_WINDOW_MS) {
    RequestService.clearRequestTime();
    if (onTerminalFailure) {
      onTerminalFailure(error);
    }
    return;
  }
  setTimeout(() => retry(retryCount + 1, startedAt), CALLBACK_RETRY_DELAY_MS);
}

export default {
  // Nhận danh sách cấu hình mô hình
  getModelList(params, callback) {
    const queryParams = new URLSearchParams({
      modelType: params.modelType,
      modelName: params.modelName || '',
      page: params.page || 0,
      limit: params.limit || 10
    }).toString();

    RequestService.sendRequest()
      .url(`${getServiceUrl()}/models/list?${queryParams}`)
      .method('GET')
      .success((res) => {
        RequestService.clearRequestTime()
        callback(res)
      })
      .networkFail((err) => {
        console.error('获取模型列表失败:', err)
        RequestService.reAjaxFun(() => {
          this.getModelList(params, callback)
        })
      }).send()
  },
  // Nhận danh sách các nhà cung cấp mô hình
  getModelProviders(modelType, callback) {
    RequestService.sendRequest()
      .url(`${getServiceUrl()}/models/${modelType}/provideTypes`)
      .method('GET')
      .success((res) => {
        RequestService.clearRequestTime()
        callback(res.data?.data || [])
      })
      .networkFail((err) => {
        console.error('获取供应器列表失败:', err)
        this.$message.error('Không thể lấy danh sách nhà cung cấp')
        RequestService.reAjaxFun(() => {
          this.getModelProviders(modelType, callback)
        })
      }).send()
  },

  // Thêm cấu hình mô hình mới
  addModel(params, callback) {
    const { modelType, provideCode, formData } = params;
    const postData = {
      id: formData.id,
      modelCode: formData.modelCode,
      modelName: formData.modelName,
      isDefault: formData.isDefault ? 1 : 0,
      isEnabled: formData.isEnabled ? 1 : 0,
      configJson: formData.configJson,
      docLink: formData.docLink,
      remark: formData.remark,
      sort: formData.sort || 0
    };

    RequestService.sendRequest()
      .url(`${getServiceUrl()}/models/${modelType}/${provideCode}`)
      .method('POST')
      .data(postData)
      .success((res) => {
        RequestService.clearRequestTime()
        callback(res)
      })
      .networkFail((err) => {
        console.error('新增模型失败:', err)
        this.$message.error(err.msg || 'Không thể thêm mô hình')
        RequestService.reAjaxFun(() => {
          this.addModel(params, callback)
        })
      }).send()
  },
  // Xóa cấu hình mô hình
  deleteModel(id, callback) {
    RequestService.sendRequest()
      .url(`${getServiceUrl()}/models/${id}`)
      .method('DELETE')
      .success((res) => {
        RequestService.clearRequestTime()
        callback(res)
      })
      .networkFail((err) => {
        console.error('删除模型失败:', err)
        this.$message.error(err.msg || 'Không thể xóa mô hình')
        RequestService.reAjaxFun(() => {
          this.deleteModel(id, callback)
        })
      }).send()
  },
  // Lấy danh sách tên model
  getModelNames(modelType, modelName, callback, onTerminalFailure, retryCount = 0, retryStartedAt = 0) {
    const retryWindowStartedAt = retryStartedAt || Date.now();
    const request = RequestService.sendRequest()
      .url(`${getServiceUrl()}/models/names`)
      .method('GET')
      .data({ modelType, modelName })
      .success((res) => {
        RequestService.clearRequestTime();
        callback(res);
      })
      .networkFail((error) => {
        retryCallbackRequest(
          (nextRetryCount, nextRetryStartedAt) => this.getModelNames(
            modelType,
            modelName,
            callback,
            onTerminalFailure,
            nextRetryCount,
            nextRetryStartedAt
          ),
          retryCount,
          onTerminalFailure,
          error,
          retryWindowStartedAt
        );
      });
    if (onTerminalFailure) {
      request.fail((error) => {
        RequestService.clearRequestTime();
        onTerminalFailure(error);
      });
    }
    request.send();
  },
  // Nhận danh sách tên mô hình LLM
  getLlmModelCodeList(modelName, callback, onTerminalFailure, retryCount = 0, retryStartedAt = 0) {
    const retryWindowStartedAt = retryStartedAt || Date.now();
    const request = RequestService.sendRequest()
      .url(`${getServiceUrl()}/models/llm/names`)
      .method('GET')
      .data({ modelName })
      .success((res) => {
        RequestService.clearRequestTime();
        callback(res);
      })
      .networkFail((error) => {
        retryCallbackRequest(
          (nextRetryCount, nextRetryStartedAt) => this.getLlmModelCodeList(
            modelName,
            callback,
            onTerminalFailure,
            nextRetryCount,
            nextRetryStartedAt
          ),
          retryCount,
          onTerminalFailure,
          error,
          retryWindowStartedAt
        );
      });
    if (onTerminalFailure) {
      request.fail((error) => {
        RequestService.clearRequestTime();
        onTerminalFailure(error);
      });
    }
    request.send();
  },
  // Nhận danh sách giai điệu mô hình
  getModelVoices(modelId, voiceName, callback, onTerminalFailure, retryCount = 0, retryStartedAt = 0) {
    const retryWindowStartedAt = retryStartedAt || Date.now();
    const queryParams = new URLSearchParams({
      voiceName: voiceName || ''
    }).toString();
    const request = RequestService.sendRequest()
      .url(`${getServiceUrl()}/models/${modelId}/voices?${queryParams}`)
      .method('GET')
      .success((res) => {
        RequestService.clearRequestTime();
        callback(res);
      })
      .networkFail((error) => {
        retryCallbackRequest(
          (nextRetryCount, nextRetryStartedAt) => this.getModelVoices(
            modelId,
            voiceName,
            callback,
            onTerminalFailure,
            nextRetryCount,
            nextRetryStartedAt
          ),
          retryCount,
          onTerminalFailure,
          error,
          retryWindowStartedAt
        );
      });
    if (onTerminalFailure) {
      request.fail((error) => {
        RequestService.clearRequestTime();
        onTerminalFailure(error);
      });
    }
    request.send();
  },
  // Nhận một cấu hình mô hình duy nhất
  getModelConfig(id, callback) {
    RequestService.sendRequest()
      .url(`${getServiceUrl()}/models/${id}`)
      .method('GET')
      .success((res) => {
        RequestService.clearRequestTime()
        callback(res)
      })
      .networkFail((err) => {
        console.error('获取模型配置失败:', err)
        this.$message.error(err.msg || 'Không thể lấy cấu hình mô hình')
        RequestService.reAjaxFun(() => {
          this.getModelConfig(id, callback)
        })
      }).send()
  },
  // Bật/tắt trạng thái mô hình
  updateModelStatus(id, status, callback) {
    RequestService.sendRequest()
      .url(`${getServiceUrl()}/models/enable/${id}/${status}`)
      .method('PUT')
      .success((res) => {
        RequestService.clearRequestTime()
        callback(res)
      })
      .networkFail((err) => {
        console.error('更新模型状态失败:', err)
        this.$message.error(err.msg || 'Không thể cập nhật trạng thái mô hình')
        RequestService.reAjaxFun(() => {
          this.updateModelStatus(id, status, callback)
        })
      }).send()
  },
  // Cập nhật cấu hình mô hình
  updateModel(params, callback) {
    const { modelType, provideCode, id, formData } = params;
    const payload = {
      ...formData,
      configJson: formData.configJson
    };
    RequestService.sendRequest()
      .url(`${getServiceUrl()}/models/${modelType}/${provideCode}/${id}`)
      .method('PUT')
      .data(payload)
      .success((res) => {
        RequestService.clearRequestTime();
        callback(res);
      })
      .networkFail((err) => {
        console.error('更新模型失败:', err);
        this.$message.error(err.msg || 'Không thể cập nhật mô hình');
        RequestService.reAjaxFun(() => {
          this.updateModel(params, callback);
        });
      }).send();
  },
  // Đặt mô hình mặc định
  setDefaultModel(id, callback) {
    RequestService.sendRequest()
      .url(`${getServiceUrl()}/models/default/${id}`)
      .method('PUT')
      .success((res) => {
        RequestService.clearRequestTime()
        callback(res)
      })
      .networkFail((err) => {
        console.error('设置默认模型失败:', err)
        this.$message.error(err.msg || 'Không thể đặt mặc định cho mô hình')
        RequestService.reAjaxFun(() => {
          this.setDefaultModel(id, callback)
        })
      }).send()
  },

  /**
   * Lấy danh sách cấu hình mô hình (hỗ trợ các tham số truy vấn)
   * @param {Object} params - Đối tượng tham số truy vấn, ví dụ { name: 'test', modelType: 1 }
   * @param {Function} callback - chức năng gọi lại
   */
  getModelProvidersPage(params, callback) {
    // Xây dựng tham số truy vấn
    const queryParams = new URLSearchParams();
    if (params.name) queryParams.append('name', params.name);
    if (params.modelType !== undefined) queryParams.append('modelType', params.modelType);
    if (params.page !== undefined) queryParams.append('page', params.page);
    if (params.limit !== undefined) queryParams.append('limit', params.limit);

    RequestService.sendRequest()
      .url(`${getServiceUrl()}/models/provider?${queryParams.toString()}`)
      .method('GET')
      .success((res) => {
        RequestService.clearRequestTime();
        callback(res);
      })
      .networkFail((err) => {
        this.$message.error(err.msg || 'Không thể lấy danh sách nhà cung cấp');
        RequestService.reAjaxFun(() => {
          this.getModelProviders(params, callback);
        });
      }).send();
  },

  /**
   * Đã thêm cấu hình nhà cung cấp mô hình
   * @param {Object} params - Đối tượng tham số yêu cầu, ví dụ { modelType: '1', ProviderCode: '1', name: '1', Fields: '1', Sort: 1 }
   * @param {Function} callback - Chức năng gọi lại thành công
   */
  addModelProvider(params, callback) {
    const postData = {
      modelType: params.modelType || '',
      providerCode: params.providerCode || '',
      name: params.name || '',
      fields: JSON.stringify(params.fields || []),
      sort: params.sort || 0
    };

    RequestService.sendRequest()
      .url(`${getServiceUrl()}/models/provider`)
      .method('POST')
      .data(postData)
      .success((res) => {
        RequestService.clearRequestTime();
        callback(res);
      })
      .networkFail((err) => {
        console.error('新增模型供应器失败:', err)
        this.$message.error(err.msg || 'Không thể thêm nhà cung cấp mô hình')
        RequestService.reAjaxFun(() => {
          this.addModelProvider(params, callback);
        });
      }).send();
  },

  /**
   * Cập nhật cấu hình nhà cung cấp mô hình
   * @param {Object} params - Đối tượng tham số yêu cầu, ví dụ { id: '111', modelType: '1', ProviderCode: '1', name: '1', Fields: '1', Sort: 1 }
   * @param {Function} callback - Chức năng gọi lại thành công
   */
  updateModelProvider(params, callback) {
    const putData = {
      id: params.id || '',
      modelType: params.modelType || '',
      providerCode: params.providerCode || '',
      name: params.name || '',
      fields: JSON.stringify(params.fields || []),
      sort: params.sort || 0
    };

    RequestService.sendRequest()
      .url(`${getServiceUrl()}/models/provider`)
      .method('PUT')
      .data(putData)
      .success((res) => {
        RequestService.clearRequestTime();
        callback(res);
      })
      .networkFail((err) => {
        this.$message.error(err.msg || 'Không thể cập nhật nhà cung cấp mô hình')
        RequestService.reAjaxFun(() => {
          this.updateModelProvider(params, callback);
        });
      }).send();
  },
  // Xóa
  deleteModelProviderByIds(ids, callback) {
    RequestService.sendRequest()
      .url(`${getServiceUrl()}/models/provider/delete`)
      .method('POST')
      .data(ids)
      .success((res) => {
        RequestService.clearRequestTime()
        callback(res);
      })
      .networkFail((err) => {
        this.$message.error(err.msg || 'Không thể xóa nhà cung cấp mô hình')
        RequestService.reAjaxFun(() => {
          this.deleteModelProviderByIds(ids, callback)
        })
      }).send()
  },
  // Nhận danh sách plugin
  getPluginFunctionList(params, callback, onTerminalFailure, retryCount = 0, retryStartedAt = 0) {
    const retryWindowStartedAt = retryStartedAt || Date.now();
    const request = RequestService.sendRequest()
      .url(`${getServiceUrl()}/models/provider/plugin/names`)
      .method('GET')
      .success((res) => {
        RequestService.clearRequestTime()
        callback(res)
      })
      .networkFail((err) => {
        if (!onTerminalFailure && this.$message) {
          this.$message.error(err.msg || 'Không thể lấy danh sách plugin');
        }
        retryCallbackRequest(
          (nextRetryCount, nextRetryStartedAt) => this.getPluginFunctionList(
            params,
            callback,
            onTerminalFailure,
            nextRetryCount,
            nextRetryStartedAt
          ),
          retryCount,
          onTerminalFailure,
          err,
          retryWindowStartedAt
        );
      });
    if (onTerminalFailure) {
      request.fail((error) => {
        RequestService.clearRequestTime();
        onTerminalFailure(error);
      });
    }
    request.send()
  },

  // Nhận danh sách mô hình RAG
  getRAGModels(callback) {
    RequestService.sendRequest()
      .url(`${getServiceUrl()}/datasets/rag-models`)
      .method('GET')
      .success((res) => {
        RequestService.clearRequestTime()
        callback(res)
      })
      .networkFail((err) => {
        console.error('获取RAG模型列表失败:', err)
        this.$message.error(err.msg || 'Không thể lấy danh sách mô hình RAG')
        RequestService.reAjaxFun(() => {
          this.getRAGModels(callback)
        })
      }).send()
  }
}
