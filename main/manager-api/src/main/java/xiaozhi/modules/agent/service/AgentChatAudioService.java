package xiaozhi.modules.agent.service;

import com.baomidou.mybatisplus.extension.repository.IRepository;

import xiaozhi.modules.agent.entity.AgentChatAudioEntity;

/**
 * Dịch vụ xử lý bảng dữ liệu âm thanh trò chuyện đại lý
 *
 * @author Goody
 * @version 1.0, 2025/5/8
 * @since 1.0.0
 */
public interface AgentChatAudioService extends IRepository<AgentChatAudioEntity> {
    /**
     * Lưu dữ liệu âm thanh
     *
     * @param audioData Dữ liệu âm thanh
     * @return ID âm thanh
     */
    String saveAudio(byte[] audioData);

    /**
     * Nhận dữ liệu âm thanh
     *
     * @param audioId ID âm thanh
     * @return dữ liệu âm thanh
     */
    byte[] getAudio(String audioId);
}
