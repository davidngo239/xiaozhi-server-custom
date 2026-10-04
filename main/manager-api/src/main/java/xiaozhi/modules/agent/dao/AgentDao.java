package xiaozhi.modules.agent.dao;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import org.apache.ibatis.annotations.Select;
import xiaozhi.common.dao.BaseDao;
import xiaozhi.modules.agent.entity.AgentEntity;
import xiaozhi.modules.agent.vo.AgentInfoVO;

@Mapper
public interface AgentDao extends BaseDao<AgentEntity> {
    /**
     * Lấy số lượng thiết bị của đại lý
     * 
     * @param agentId đại lý ID đại lý
     * @return số lượng thiết bị
     */
    Integer getDeviceCountByAgentId(@Param("agentId") String agentId);

    /**
     * Truy vấn thông tin tác nhân mặc định của thiết bị tương ứng dựa trên địa chỉ MAC của thiết bị
     *
     * @param macAddress chỉ MAC của thiết bị
     * @return thông tin đại lý mặc định
     */
    @Select(" SELECT a.* FROM ai_device d " +
            " LEFT JOIN ai_agent a ON d.agent_id = a.id " +
            " WHERE d.mac_address = #{macAddress} " +
            " ORDER BY d.id DESC LIMIT 1")
    AgentEntity getDefaultAgentByMacAddress(@Param("macAddress") String macAddress);

    /**
     * Thông tin tác nhân truy vấn dựa trên ID, bao gồm thông tin phần bổ trợ
     *
     * @param agentId đại lý ID đại lý
     */
    AgentInfoVO selectAgentInfoById(@Param("agentId") String agentId);

    /**
     * Khóa bản ghi tổng thể của tác nhân, dùng để tuần tự hóa việc ghi cấu hình cho cùng một tác nhân
     *
     * @param agentId đại lý ID đại lý
     */
    AgentEntity selectByIdForUpdate(@Param("agentId") String agentId);

    /**
     * Ghi chính xác các trường Tác nhân được bao phủ bởi ảnh chụp nhanh, bao gồm các giá trị null trong ảnh chụp nhanh mục tiêu.
     * Các trường không thuộc ảnh chụp nhanh, chẳng hạn như thông tin về quyền sở hữu và tạo của người dùng, sẽ không được cập nhật.
     *
     * @param agent Tác nhân mà ảnh chụp nhanh mục tiêu đã được áp dụng
     * @return Số lượng hàng bị ảnh hưởng
     */
    int updateSnapshotFields(@Param("agent") AgentEntity agent);
}
