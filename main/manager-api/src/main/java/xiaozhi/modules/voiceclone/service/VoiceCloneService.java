package xiaozhi.modules.voiceclone.service;

import java.util.List;
import java.util.Map;

import org.springframework.web.multipart.MultipartFile;

import xiaozhi.common.page.PageData;
import xiaozhi.common.service.BaseService;
import xiaozhi.modules.voiceclone.dto.VoiceCloneDTO;
import xiaozhi.modules.voiceclone.dto.VoiceCloneResponseDTO;
import xiaozhi.modules.voiceclone.entity.VoiceCloneEntity;

/**
 * Quản lý bản sao âm thanh
 */
public interface VoiceCloneService extends BaseService<VoiceCloneEntity> {

    /**
     * Truy vấn trang
     */
    PageData<VoiceCloneEntity> page(Map<String, Object> params);

    /**
     * Lưu bản sao âm thanh
     */
    void save(VoiceCloneDTO dto);

    /**
     * Xóa hàng loạt
     */
    void delete(String[] ids);

    /**
     * Truy vấn danh sách bản sao âm thanh dựa trên ID người dùng
     * 
     * @param userId ID người dùng
     * @return danh sách bản sao âm thanh
     */
    List<VoiceCloneEntity> getByUserId(Long userId);

    /**
     * Truy vấn được phân trang cho danh sách bản sao âm thanh với tên model và tên người dùng
     */
    PageData<VoiceCloneResponseDTO> pageWithNames(Map<String, Object> params);

    /**
     * Truy vấn thông tin bản sao âm thanh với tên model và tên người dùng dựa trên ID
     */
    VoiceCloneResponseDTO getByIdWithNames(String id);

    /**
     * Truy vấn danh sách bản sao âm thanh với tên model dựa trên ID người dùng
     */
    List<VoiceCloneResponseDTO> getByUserIdWithNames(Long userId);

    /**
     * Tải lên tập tin âm thanh
     */
    void uploadVoice(String id, MultipartFile voiceFile) throws Exception;

    /**
     * Cập nhật tên bản sao âm thanh
     */
    void updateName(String id, String name);

    /**
     * Nhận dữ liệu âm thanh
     */
    byte[] getVoiceData(String id);

    /**
     * Sao chép âm thanh và gọi công cụ Volcano để đào tạo tái tạo giọng nói
     * 
     * @param cloneId ID bản ghi bản sao giọng nói
     */
    void cloneAudio(String cloneId);
}
