package xiaozhi.modules.agent.service;

import java.util.List;

import xiaozhi.modules.agent.dto.AgentVoicePrintSaveDTO;
import xiaozhi.modules.agent.dto.AgentVoicePrintUpdateDTO;
import xiaozhi.modules.agent.vo.AgentVoicePrintVO;

/**
 * Dịch vụ xử lý giọng nói thông minh
 *
 * @author zjy
 */
public interface AgentVoicePrintService {
    /**
     * Thêm giọng nói mới cho đại lý
     *
     * @param dto lưu dữ liệu giọng nói của tổng đài viên
     * @return T: thành công F: thất bại
     */
    boolean insert(AgentVoicePrintSaveDTO dto);

    /**
     * Xóa dấu vân tay của đặc vụ
     *
     * @param userId hiện đã đăng nhập id người dùng
     * @param voicePrintId id giọng nói
     * @return Có thành công không T: Thành công F: Thất bại
     */
    boolean delete(Long userId, String voicePrintId);

    /**
     * Nhận tất cả dữ liệu giọng nói của tác nhân được chỉ định
     *
     * @param userId hiện đã đăng nhập id người dùng
     * @param agentId id đại lý
     * @return Thu thập dữ liệu Voiceprint
     */
    List<AgentVoicePrintVO> list(Long userId, String agentId);

    /**
     * Cập nhật dữ liệu giọng nói ngón tay của đại lý
     *
     * @param userId hiện đã đăng nhập id người dùng
     * @param dto đã sửa đổi dữ liệu giọng nói
     * @return Có thành công không T: Thành công F: Thất bại
     */
    boolean update(Long userId, AgentVoicePrintUpdateDTO dto);

}
