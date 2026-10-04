package xiaozhi.modules.agent.service;

import java.util.List;
import java.util.Map;

import xiaozhi.common.page.PageData;
import xiaozhi.common.service.BaseService;
import xiaozhi.modules.agent.dto.AgentCreateDTO;
import xiaozhi.modules.agent.dto.AgentDTO;
import xiaozhi.modules.agent.dto.AgentMemoryDTO;
import xiaozhi.modules.agent.dto.AgentUpdateDTO;
import xiaozhi.modules.agent.entity.AgentEntity;
import xiaozhi.modules.agent.vo.AgentInfoVO;

/**
 * Dịch vụ xử lý bề mặt cơ thể thông minh
 *
 * @author Goody
 * @version 1.0, 2025/4/30
 * @since 1.0.0
 */
public interface AgentService extends BaseService<AgentEntity> {
    /**
     * Lấy danh sách đại lý quản trị viên
     *
     * @param params số truy vấn thông số
     * @return dữ liệu được phân trang
     */
    PageData<AgentEntity> adminAgentList(Map<String, Object> params);

    /**
     * Nhận đại lý dựa trên ID
     *
     * @param id ID đại lý
     * @return thực thể đại lý
     */
    AgentInfoVO getAgentById(String id);

    /**
     * Nhận các tác nhân mà người dùng hiện tại có quyền truy cập dựa trên ID
     *
     * @param id ID đại lý
     * @param userId ID người dùng hiện tại
     * @return thực thể đại lý
     */
    AgentInfoVO getAgentById(String id, Long userId);

    /**
     * Chèn tác nhân
     *
     * @param entity thể đại lý thực thể
     * @return xem có thành công không
     */
    boolean insert(AgentEntity entity);

    /**
     * Xóa tác nhân dựa trên ID người dùng
     *
     * @param userId ID người dùng
     */
    void deleteAgentByUserId(Long userId);

    /**
     * Xóa một tác nhân và dữ liệu liên quan của nó
     *
     * @param agentId đại lý ID đại lý
     */
    void deleteAgent(String agentId);

    /**
     * Lấy danh sách tác nhân người dùng
     *
     * @param userId ID người dùng
     * @param keyword Tìm kiếm từ khóa
     * @param searchType Loại tìm kiếm (tên - tìm kiếm theo tên, mac - tìm kiếm theo địa chỉ MAC)
     * @return danh sách đại lý
     */
    List<AgentDTO> getUserAgents(Long userId, String keyword, String searchType);

    /**
     * Lấy số lượng thiết bị dựa trên ID đại lý
     *
     * @param agentId ID đại lý
     * @return số lượng thiết bị
     */
    Integer getDeviceCountByAgentId(String agentId);

    /**
     * Truy vấn thông tin tác nhân mặc định của thiết bị tương ứng dựa trên địa chỉ MAC của thiết bị
     *
     * @param macAddress Địa chỉ MAC của thiết bị
     * @return Thông tin tác nhân mặc định, trả về null nếu nó không tồn tại
     */
    AgentEntity getDefaultAgentByMacAddress(String macAddress);

    /**
     * Kiểm tra xem người dùng có quyền truy cập vào tác nhân hay không
     *
     * @param agentId ID đại lý
     * @param userId ID người dùng
     * @return có được phép không
     */
    boolean checkAgentPermission(String agentId, Long userId);

    /**
     * Cập nhật đại lý
     *
     * @param agentId ID đại lý
     * @param dto Cập nhật các thông tin cần thiết của đại lý
     */
    void updateAgentById(String agentId, AgentUpdateDTO dto);

    /**
     * Cập nhật các tác nhân mà người dùng hiện tại có quyền truy cập
     *
     * @param agentId ID đại lý
     * @param dto Cập nhật các thông tin cần thiết của đại lý
     * @param userId ID người dùng hiện tại
     */
    void updateAgentById(String agentId, AgentUpdateDTO dto, Long userId);

    /**
     * Cập nhật bộ nhớ tác nhân mà người dùng hiện tại có quyền truy cập dựa trên địa chỉ MAC của thiết bị
     *
     * @param macAddress Địa chỉ MAC của thiết bị
     * @param dto bộ nhớ tác nhân
     * @param userId ID người dùng hiện tại
     */
    void updateAgentMemoryByDeviceMacAddress(String macAddress, AgentMemoryDTO dto, Long userId);

    /**
     * Xóa một tác nhân mà người dùng hiện tại có quyền truy cập
     *
     * @param agentId ID đại lý
     * @param userId ID người dùng hiện tại
     */
    void deleteAgentById(String agentId, Long userId);

    /**
     * Cập nhật đại lý
     *
     * @param agentId ID đại lý
     * @param dto Cập nhật các thông tin cần thiết của đại lý
     * @param createSnapshot Có tạo ảnh chụp nhanh cấu hình hay không
     */
    void updateAgentById(String agentId, AgentUpdateDTO dto, boolean createSnapshot);

    /**
     * Tạo một đại lý
     *
     * @param dto Thông tin cần thiết để tạo đại lý
     * @return ID đại lý đã tạo
     */
    String createAgent(AgentCreateDTO dto);


}
