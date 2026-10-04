package xiaozhi.modules.agent.dao;

import org.apache.ibatis.annotations.Mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;

import xiaozhi.modules.agent.entity.AgentChatAudioEntity;

/**
 * {@link AgentChatAudioEntity} Dữ liệu âm thanh trò chuyện của tác nhân Đối tượng Dao
 *
 * @author Goody
 * @version 1.0, 2025/5/8
 * @since 1.0.0
 */
@Mapper
public interface AiAgentChatAudioDao extends BaseMapper<AgentChatAudioEntity> {
}