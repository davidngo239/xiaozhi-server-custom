package xiaozhi.modules.voiceclone.dao;

import java.util.List;

import org.apache.ibatis.annotations.Mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;

import xiaozhi.modules.model.dto.VoiceDTO;
import xiaozhi.modules.voiceclone.entity.VoiceCloneEntity;

/**
 * nhân bản âm thanh
 */
@Mapper
public interface VoiceCloneDao extends BaseMapper<VoiceCloneEntity> {
    /**
     * Lấy danh sách âm sắc được người dùng huấn luyện thành công
     * 
     * @param modelId ID mô hình
     * @param userId ID người dùng
     * @return Danh sách các âm sắc được huấn luyện thành công
     */
    List<VoiceDTO> getTrainSuccess(String modelId, Long userId);

}
