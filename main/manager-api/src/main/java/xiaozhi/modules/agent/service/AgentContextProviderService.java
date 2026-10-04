package xiaozhi.modules.agent.service;

import xiaozhi.common.service.BaseService;
import xiaozhi.modules.agent.entity.AgentContextProviderEntity;

public interface AgentContextProviderService extends BaseService<AgentContextProviderEntity> {
    /**
     * Nhận cấu hình nguồn ngữ cảnh dựa trên ID tác nhân
     * @param agentId đại lý ID đại lý
     * @return thực thể cấu hình nguồn ngữ cảnh
     */
    AgentContextProviderEntity getByAgentId(String agentId);

    /**
     * Lưu hoặc cập nhật cấu hình nguồn ngữ cảnh
     * @param entity thể thực thể
     */
    void saveOrUpdateByAgentId(AgentContextProviderEntity entity);

    /**
     * Xóa cấu hình nguồn ngữ cảnh dựa trên ID tác nhân
     * @param agentId đại lý ID đại lý
     */
    void deleteByAgentId(String agentId);
}
