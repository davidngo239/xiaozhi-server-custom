package xiaozhi.modules.correctword.service;

import java.util.List;
import java.util.Map;

import xiaozhi.common.page.PageData;
import xiaozhi.modules.correctword.dto.CorrectWordFileCreateDTO;
import xiaozhi.modules.correctword.vo.CorrectWordFileVO;
import xiaozhi.modules.correctword.vo.CorrectWordSimpleVO;

public interface CorrectWordFileService {

    /**
     * Tạo một tập tin từ thay thế
     *
     * @param dto tạo tham số
     * @return fileVO
     */
    CorrectWordFileVO createFile(CorrectWordFileCreateDTO dto);

    /**
     * Sửa đổi file word thay thế (thay thế tất cả các mục)
     *
     * @param fileId ID tệp
     * @param dto sửa đổi tham số
     */
    void updateFile(String fileId, CorrectWordFileCreateDTO dto);

    /**
     * Lấy danh sách file word thay thế của người dùng hiện tại
     *
     * @param params số phân trang
     * @return dữ liệu được phân trang
     */
    PageData<CorrectWordFileVO> listFiles(Map<String, Object> params);

    /**
     * Lấy danh sách file word thay thế của người dùng hiện tại (không đánh số trang, dùng để lựa chọn thả xuống)
     *
     * @return danh sách tập tin
     */
    List<CorrectWordFileVO> listAllFiles();

    /**
     * Lấy nội dung gốc của file (để tải về)
     *
     * @param fileId ID tệp
     * thực thể tệp @return
     */
    CorrectWordFileVO getFileContent(String fileId);

    /**
     * Xóa tệp từ thay thế và tất cả các mục nhập và bản ghi liên quan của nó
     *
     * @param fileId ID tệp
     */
    void deleteFile(String fileId);

    /**
     * Xóa bản ghi liên kết tệp từ thay thế được liên kết với tác nhân (không xóa chính tệp đó)
     *
     * @param agentId đại lý ID đại lý
     */
    void deleteMappingsByAgentId(String agentId);

    /**
     * Nhận tất cả các điều khoản thay thế của đại lý (phiên bản rút gọn, dành cho sử dụng thiết bị)
     *
     * @param agentId đại lý ID đại lý
     * @return danh sách từ thay thế
     */
    List<CorrectWordSimpleVO> getAllItemsByAgentId(String agentId);

    /**
     * Lấy danh sách ID file word thay thế liên kết với tác nhân
     *
     * @param agentId đại lý ID đại lý
     * @return danh sách ID tập tin
     */
    List<String> getAgentCorrectWordFileIds(String agentId);

    /**
     * Lưu file word thay thế liên kết với đại lý (thay thế đầy đủ)
     *
     * @param agentId đại lý ID đại lý
     * @param fileIds danh sách ID tệp
     */
    void saveAgentCorrectWords(String agentId, List<String> fileIds);

    /**
     * Xóa hàng loạt file word thay thế
     *
     * @param fileIds danh sách ID tệp
     */
    void batchDeleteFiles(List<String> fileIds);
}
