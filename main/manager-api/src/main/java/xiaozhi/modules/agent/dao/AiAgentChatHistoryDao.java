package xiaozhi.modules.agent.dao;

import java.util.List;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;

import xiaozhi.modules.agent.entity.AgentChatHistoryEntity;

/**
 * {@link AgentChatHistoryEntity} Lịch sử trò chuyện của đại lý Đối tượng Dao
 *
 * @author Goody
 * @version 1.0, 2025/4/30
 * @since 1.0.0
 */
@Mapper
public interface AiAgentChatHistoryDao extends BaseMapper<AgentChatHistoryEntity> {

    /**
     * Delete chat history based on agent ID
     *
     * @param agentId đại lý ID đại lý
     */
    void deleteHistoryByAgentId(String agentId);

    /**
     * Xóa ID âm thanh dựa trên ID tác nhân
     *
     * @param agentId đại lý ID đại lý
     */
    void deleteAudioIdByAgentId(String agentId);

    /**
     * Nhận danh sách tất cả ID âm thanh dựa trên ID tác nhân
     *
     * @param agentId đại lý ID đại lý
     * @return Danh sách ID âm thanh
     */
    List<String> getAudioIdsByAgentId(String agentId);

    /**
     * Xóa âm thanh theo đợt
     *
     * @param audioIds Danh sách ID âm thanh
     */
    void deleteAudioByIds(@Param("audioIds") List<String> audioIds);
}
