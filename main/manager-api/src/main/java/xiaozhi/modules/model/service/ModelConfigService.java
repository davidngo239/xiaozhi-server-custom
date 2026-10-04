package xiaozhi.modules.model.service;

import java.util.List;
import java.util.Map;

import xiaozhi.common.page.PageData;
import xiaozhi.common.service.BaseService;
import xiaozhi.modules.model.dto.LlmModelBasicInfoDTO;
import xiaozhi.modules.model.dto.ModelBasicInfoDTO;
import xiaozhi.modules.model.dto.ModelConfigBodyDTO;
import xiaozhi.modules.model.dto.ModelConfigDTO;
import xiaozhi.modules.model.entity.ModelConfigEntity;

public interface ModelConfigService extends BaseService<ModelConfigEntity> {

    List<ModelBasicInfoDTO> getModelCodeList(String modelType, String modelName);

    List<LlmModelBasicInfoDTO> getLlmModelCodeList(String modelName);

    PageData<ModelConfigDTO> getPageList(String modelType, String modelName, String page, String limit);

    ModelConfigDTO add(String modelType, String provideCode, ModelConfigBodyDTO modelConfigBodyDTO);

    ModelConfigDTO edit(String modelType, String provideCode, String id, ModelConfigBodyDTO modelConfigBodyDTO);

    void delete(String id);

    /**
     * Nhận tên model dựa trên ID
     * 
     * @param id Mã mẫu
     * @return tên mẫu
     */
    String getModelNameById(String id);

    /**
     * Nhận cấu hình mô hình dựa trên ID
     * 
     * @param id Mã mẫu
     * Thực thể cấu hình mô hình @return
     */
    ModelConfigEntity getModelByIdFromCache(String id);

    /**
     * Đặt mô hình mặc định
     *
     * @param modelType loại mô hình
     * @param isDefault Là mặc định (1: có, 0: không)
     */
    void setDefaultModel(String modelType, int isDefault);

    /**
     * Nhận danh sách các nền tảng TTS đủ điều kiện
     *
     * @return Danh sách nền tảng TTS (id và modelName)
     */
    List<Map<String, Object>> getTtsPlatformList();

    /**
     * Nhận tất cả các cấu hình mô hình được kích hoạt dựa trên loại mô hình
     *
     * @param modelType loại mô hình (chẳng hạn như: LLM, TTS, ASR, v.v.)
     * Danh sách cấu hình mô hình đã bật @return
     */
    List<ModelConfigEntity> getEnabledModelsByType(String modelType);
}
