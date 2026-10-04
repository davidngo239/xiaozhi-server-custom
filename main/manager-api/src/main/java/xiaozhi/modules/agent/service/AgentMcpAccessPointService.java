package xiaozhi.modules.agent.service;


import java.util.List;

/**
 * Dịch vụ xử lý điểm truy cập Agent Mcp
 *
 * @author zjy
 */
public interface AgentMcpAccessPointService {
    /**
     * Lấy địa chỉ điểm truy cập mcp của đại lý
     * @param id id đại lý
     * @return địa chỉ điểm truy cập mcp
     */
   String getAgentMcpAccessAddress(String id);

    /**
     * Lấy danh sách công cụ hiện có của điểm truy cập mcp của đại lý
     * @param id id đại lý
     * Danh sách công cụ @return
     */
   List<String> getAgentMcpToolsList(String id);
}
