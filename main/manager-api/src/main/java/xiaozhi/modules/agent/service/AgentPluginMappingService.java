package xiaozhi.modules.agent.service;

import java.util.List;

import com.baomidou.mybatisplus.extension.repository.IRepository;

import xiaozhi.modules.agent.entity.AgentPluginMapping;

/**
 * @description Dịch vụ vận hành cơ sở dữ liệu cho bảng [ai_agent_plugin_mapping (bảng ánh xạ duy nhất giữa Tác nhân và trình cắm)]
 * @createDate 2025-05-25 22:33:17
 */
public interface AgentPluginMappingService extends IRepository<AgentPluginMapping> {

    /**
     * Nhận thông số plug-in dựa trên id tác nhân
     *
     * @param agentId
     * @return
     */
    List<AgentPluginMapping> agentPluginParamsByAgentId(String agentId);

    /**
     * Xóa tham số plugin dựa trên id tác nhân
     *
     * @param agentId
     */
    void deleteByAgentId(String agentId);

    /**
     * Xóa tất cả ánh xạ plugin của tác nhân dựa trên ID plugin
     *
     * @param pluginId Mã plugin
     */
    void deleteByPluginId(String pluginId);
}
