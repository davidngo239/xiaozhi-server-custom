package xiaozhi.modules.agent.dao;

import org.apache.ibatis.annotations.Mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;

import xiaozhi.modules.agent.entity.AgentTemplateEntity;

/**
 * @author chenerlei
 * @description Hoạt động cơ sở dữ liệu Mapper cho bảng [ai_agent_template (bảng mẫu cấu hình tác nhân)]
 * @createDate 2025-03-22 11:48:18
 */
@Mapper
public interface AgentTemplateDao extends BaseMapper<AgentTemplateEntity> {

}
