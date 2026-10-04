import { getServiceUrl } from '../api';
import RequestService from '../httpRequest';

/**
 * Nhận mã thông báo xác thực
 */
function getAuthToken() {
  return localStorage.getItem('token') || '';
}

/**
 * Trình bao bọc yêu cầu API chung
 * @param {Object} config - Yêu cầu cấu hình
 * @param {string} config.url - URL yêu cầu
 * @param {string} config.method - phương thức yêu cầu
 * @param {Object} [config.data] - Dữ liệu yêu cầu
 * @param {Object} [config.headers] - tiêu đề yêu cầu bổ sung
 * @param {Function} config.callback - gọi lại thành công
 * @param {Function} [config.errorCallback] - gọi lại lỗi
 * @param {string} [config.errorMessage] - thông báo lỗi
 * @param {Function} [config.retryFunction] - chức năng thử lại
 */
function makeApiRequest(config) {
  const token = getAuthToken();
  const { url, method, data, headers, callback, errorCallback, errorMessage, retryFunction } = config;

  const requestBuilder = RequestService.sendRequest()
    .url(url)
    .method(method)
    .header({
      'Authorization': `Bearer ${token}`,
      ...headers
    });

  if (data) {
    requestBuilder.data(data);
  }

  requestBuilder
    .success((res) => {
      RequestService.clearRequestTime();
      callback(res);
    })
    .fail((err) => {
      console.error(errorMessage || 'Thao tác thất bại', err);
      if (errorCallback) {
        errorCallback(err);
      }
    })
    .networkFail(() => {
      if (retryFunction) {
        RequestService.reAjaxFun(() => {
          retryFunction();
        });
      }
    }).send();
}

/**
 * API liên quan đến quản lý cơ sở kiến thức
 */
export default {
  /**
   * Lấy danh sách cơ sở kiến thức
   * @param {Object} params - Tham số truy vấn
   * @param {Function} callback - chức năng gọi lại
   * @param {Function} errorCallback - gọi lại lỗi
   */
  getKnowledgeBaseList(params, callback, errorCallback) {
    const queryParams = new URLSearchParams({
      page: params.page,
      page_size: params.page_size,
      name: params.name || ''
    }).toString();

    makeApiRequest({
      url: `${getServiceUrl()}/datasets?${queryParams}`,
      method: 'GET',
      callback: callback,
      errorCallback: errorCallback,
      errorMessage: 'Không thể lấy danh sách kho tri thức',
      retryFunction: () => this.getKnowledgeBaseList(params, callback, errorCallback)
    });
  },

  /**
   * Tạo nền tảng kiến thức
   * @param {Object} data - Dữ liệu cơ sở tri thức
   * @param {Function} callback - chức năng gọi lại
   * @param {Function} errorCallback - gọi lại lỗi
   */
  createKnowledgeBase(data, callback, errorCallback) {
    console.log('createKnowledgeBase called with data:', data);
    console.log('API URL:', `${getServiceUrl()}/datasets`);

    makeApiRequest({
      url: `${getServiceUrl()}/datasets`,
      method: 'POST',
      data: data,
      headers: { 'Content-Type': 'application/json' },
      callback: (res) => {
        console.log('createKnowledgeBase success response:', res);
        callback(res);
      },
      errorCallback: (err) => {
        console.error('创建知识库失败:', err);
        if (err.response) {
          console.error('Error response data:', err.response.data);
          console.error('Error response status:', err.response.status);
        }
        if (errorCallback) {
          errorCallback(err);
        }
      },
      errorMessage: 'Không thể tạo kho tri thức',
      retryFunction: () => this.createKnowledgeBase(data, callback, errorCallback)
    });
  },

  /**
   * Cập nhật cơ sở kiến thức
   * @param {string} datasetId -ID cơ sở kiến thức
   * @param {Object} data - Cập nhật dữ liệu
   * @param {Function} callback - chức năng gọi lại
   * @param {Function} errorCallback - gọi lại lỗi
   */
  updateKnowledgeBase(datasetId, data, callback, errorCallback) {
    console.log('updateKnowledgeBase called with datasetId:', datasetId, 'data:', data);
    console.log('API URL:', `${getServiceUrl()}/datasets/${datasetId}`);

    makeApiRequest({
      url: `${getServiceUrl()}/datasets/${datasetId}`,
      method: 'PUT',
      data: data,
      headers: { 'Content-Type': 'application/json' },
      callback: callback,
      errorCallback: errorCallback,
      errorMessage: 'Không thể cập nhật kho tri thức',
      retryFunction: () => this.updateKnowledgeBase(datasetId, data, callback, errorCallback)
    });
  },

  /**
   * Xóa một cơ sở kiến thức duy nhất
   * @param {string} datasetId -ID cơ sở kiến thức
   * @param {Function} callback - chức năng gọi lại
   * @param {Function} errorCallback - gọi lại lỗi
   */
  deleteKnowledgeBase(datasetId, callback, errorCallback) {
    console.log('deleteKnowledgeBase called with datasetId:', datasetId);
    console.log('API URL:', `${getServiceUrl()}/datasets/${datasetId}`);

    makeApiRequest({
      url: `${getServiceUrl()}/datasets/${datasetId}`,
      method: 'DELETE',
      callback: callback,
      errorCallback: errorCallback,
      errorMessage: 'Không thể xóa kho tri thức',
      retryFunction: () => this.deleteKnowledgeBase(datasetId, callback, errorCallback)
    });
  },

  /**
   * Xóa cơ sở kiến thức theo đợt
   * @param {string|Array} ids -Chuỗi hoặc mảng ID cơ sở kiến thức
   * @param {Function} callback - chức năng gọi lại
   * @param {Function} errorCallback - gọi lại lỗi
   */
  deleteKnowledgeBases(ids, callback, errorCallback) {
    // Đảm bảo id là chuỗi được định dạng chính xác
    const idsStr = Array.isArray(ids) ? ids.join(',') : ids;

    makeApiRequest({
      url: `${getServiceUrl()}/datasets/batch?ids=${idsStr}`,
      method: 'DELETE',
      callback: callback,
      errorCallback: errorCallback,
      errorMessage: 'Không thể xóa hàng loạt kho tri thức',
      retryFunction: () => this.deleteKnowledgeBases(ids, callback, errorCallback)
    });
  },

  /**
   * Nhận danh sách tài liệu
   * @param {string} datasetId -ID cơ sở kiến thức
   * @param {Object} params - Tham số truy vấn
   * @param {Function} callback - chức năng gọi lại
   * @param {Function} errorCallback - gọi lại lỗi
   */
  getDocumentList(datasetId, params, callback, errorCallback) {
    const queryParams = new URLSearchParams({
      page: params.page,
      page_size: params.page_size,
      name: params.name || ''
    }).toString();

    makeApiRequest({
      url: `${getServiceUrl()}/datasets/${datasetId}/documents?${queryParams}`,
      method: 'GET',
      callback: callback,
      errorCallback: errorCallback,
      errorMessage: 'Không thể lấy danh sách tài liệu',
      retryFunction: () => this.getDocumentList(datasetId, params, callback, errorCallback)
    });
  },

  /**
   * Tải tài liệu lên
   * @param {string} datasetId -ID cơ sở kiến thức
   * @param {Object} formData - dữ liệu biểu mẫu
   * @param {Function} callback - chức năng gọi lại
   * @param {Function} errorCallback - gọi lại lỗi
   */
  uploadDocument(datasetId, formData, callback, errorCallback) {
    makeApiRequest({
      url: `${getServiceUrl()}/datasets/${datasetId}/documents`,
      method: 'POST',
      data: formData,
      headers: { 'Content-Type': 'multipart/form-data' },
      callback: callback,
      errorCallback: errorCallback,
      errorMessage: 'Không thể tải lên tài liệu',
      retryFunction: () => this.uploadDocument(datasetId, formData, callback, errorCallback)
    });
  },

  /**
   * Phân tích tài liệu
   * @param {string} datasetId -ID cơ sở kiến thức
   * @param {string} documentId - ID tài liệu
   * @param {Function} callback - chức năng gọi lại
   * @param {Function} errorCallback - gọi lại lỗi
   */
  parseDocument(datasetId, documentId, callback, errorCallback) {
    const requestBody = {
      document_ids: [documentId]
    };

    makeApiRequest({
      url: `${getServiceUrl()}/datasets/${datasetId}/chunks`,
      method: 'POST',
      data: requestBody,
      headers: { 'Content-Type': 'application/json' },
      callback: callback,
      errorCallback: errorCallback,
      errorMessage: 'Không thể phân tích tài liệu',
      retryFunction: () => this.parseDocument(datasetId, documentId, callback, errorCallback)
    });
  },

  /**
   * Xóa tài liệu
   * @param {string} datasetId -ID cơ sở kiến thức
   * @param {string} documentId - ID tài liệu
   * @param {Function} callback - chức năng gọi lại
   * @param {Function} errorCallback - gọi lại lỗi
   */
  deleteDocument(datasetId, documentId, callback, errorCallback) {
    makeApiRequest({
      url: `${getServiceUrl()}/datasets/${datasetId}/documents/${documentId}`,
      method: 'DELETE',
      callback: callback,
      errorCallback: errorCallback,
      errorMessage: 'Không thể xóa tài liệu',
      retryFunction: () => this.deleteDocument(datasetId, documentId, callback, errorCallback)
    });
  },

  /**
   * Nhận danh sách các lát tài liệu
   * @param {string} datasetId -ID cơ sở kiến thức
   * @param {string} documentId - ID tài liệu
   * @param {Object} params - Tham số truy vấn
   * @param {Function} callback - chức năng gọi lại
   * @param {Function} errorCallback - gọi lại lỗi
   */
  listChunks(datasetId, documentId, params, callback, errorCallback) {
    let queryParams = new URLSearchParams({
      page: params.page || 1,
      page_size: params.page_size || 10
    }).toString();

    // Thêm thông số tìm kiếm từ khóa
    if (params.keywords) {
      queryParams += `&keywords=${encodeURIComponent(params.keywords)}`;
    }

    makeApiRequest({
      url: `${getServiceUrl()}/datasets/${datasetId}/documents/${documentId}/chunks?${queryParams}`,
      method: 'GET',
      callback: callback,
      errorCallback: errorCallback,
      errorMessage: 'Không thể lấy danh sách đoạn văn bản',
      retryFunction: () => this.listChunks(datasetId, documentId, params, callback, errorCallback)
    });
  },

  /**
   * kiểm tra thu hồi
   * @param {string} datasetId -ID cơ sở kiến thức
   * @param {Object} data - Nhớ lại các thông số kiểm tra
   * @param {Function} callback - chức năng gọi lại
   * @param {Function} errorCallback - gọi lại lỗi
   */
  retrievalTest(datasetId, data, callback, errorCallback) {
    makeApiRequest({
      url: `${getServiceUrl()}/datasets/${datasetId}/retrieval-test`,
      method: 'POST',
      data: data,
      headers: { 'Content-Type': 'application/json' },
      callback: callback,
      errorCallback: errorCallback,
      errorMessage: 'Kiểm tra truy xuất thất bại',
      retryFunction: () => this.retrievalTest(datasetId, data, callback, errorCallback)
    });
  }

};