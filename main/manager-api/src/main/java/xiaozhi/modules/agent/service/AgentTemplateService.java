package xiaozhi.modules.agent.service;

import com.baomidou.mybatisplus.extension.repository.IRepository;

import xiaozhi.modules.agent.entity.AgentTemplateEntity;

/**
 * @author chenerlei
 * @description Dịch vụ vận hành cơ sở dữ liệu cho bảng [ai_agent_template (bảng mẫu cấu hình tác nhân)]
 * @createDate 2025-03-22 11:48:18
 */
public interface AgentTemplateService extends IRepository<AgentTemplateEntity> {

    /**
     * Nhận mẫu mặc định
     * 
     * @return thực thể mẫu mặc định
     */
    AgentTemplateEntity getDefaultTemplate();

    /**
     * Cập nhật ID mẫu trong mẫu mặc định
     * 
     * @param modelType loại mô hình
     * @param modelId ID mô hình
     */
    void updateDefaultTemplateModelId(String modelType, String modelId);

    /**
     * Sắp xếp lại các mẫu còn lại sau khi xóa chúng
     * 
     * @param deletedSort xóaSắp xếp sắp xếp giá trị của các mẫu đã xóa
     */
    void reorderTemplatesAfterDelete(Integer deletedSort);

    /**
     * Lấy số sắp xếp có sẵn tiếp theo (tìm số thứ tự nhỏ nhất chưa sử dụng)
     * 
     * @return số sắp xếp có sẵn tiếp theo
     */
    Integer getNextAvailableSort();
}
