package xiaozhi.modules.agent.service.impl;

import org.springframework.stereotype.Service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.UpdateWrapper;
import com.baomidou.mybatisplus.spring.repository.CrudRepository;

import xiaozhi.modules.agent.dao.AgentTemplateDao;
import xiaozhi.modules.agent.entity.AgentTemplateEntity;
import xiaozhi.modules.agent.service.AgentTemplateService;

import java.util.List;
import java.util.Objects;
import java.util.stream.Collectors;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;

/**
 * @author chenerlei
 * @description Vận hành cơ sở dữ liệu Triển khai dịch vụ cho bảng [ai_agent_template (bảng mẫu cấu hình tác nhân)]
 * @createDate 2025-03-22 11:48:18
 */
@Service
public class AgentTemplateServiceImpl extends CrudRepository<AgentTemplateDao, AgentTemplateEntity>
        implements AgentTemplateService {

    /**
     * Nhận mẫu mặc định
     * 
     * @return thực thể mẫu mặc định
     */
    public AgentTemplateEntity getDefaultTemplate() {
        LambdaQueryWrapper<AgentTemplateEntity> wrapper = new LambdaQueryWrapper<>();
        wrapper.orderByAsc(AgentTemplateEntity::getSort)
                .last("LIMIT 1");
        return this.getOne(wrapper);
    }

    /**
     * Cập nhật ID mẫu trong mẫu mặc định
     * 
     * @param modelType loại mô hình
     * @param modelId ID mô hình
     */
    @Override
    public void updateDefaultTemplateModelId(String modelType, String modelId) {
        modelType = modelType.toUpperCase();
        // Nếu là mẫu giẻ rách thì không cần cập nhật
        if (modelType.equals("RAG")) {
            return;
        }

        UpdateWrapper<AgentTemplateEntity> wrapper = new UpdateWrapper<>();
        switch (modelType) {
            case "ASR":
                wrapper.set("asr_model_id", modelId);
                break;
            case "VAD":
                wrapper.set("vad_model_id", modelId);
                break;
            case "LLM":
                wrapper.set("llm_model_id", modelId);
                break;
            case "TTS":
                wrapper.set("tts_model_id", modelId);
                wrapper.set("tts_voice_id", null);
                break;
            case "VLLM":
                wrapper.set("vllm_model_id", modelId);
                break;
            case "MEMORY":
                wrapper.set("mem_model_id", modelId);
                break;
            case "INTENT":
                wrapper.set("intent_model_id", modelId);
                break;
        }
        wrapper.ge("sort", 0);
        update(wrapper);
    }

    @Override
    public void reorderTemplatesAfterDelete(Integer deletedSort) {
        if (deletedSort == null) {
            return;
        }
        
        // Truy vấn tất cả các bản ghi có giá trị sắp xếp lớn hơn mẫu đã xóa
        UpdateWrapper<AgentTemplateEntity> updateWrapper = new UpdateWrapper<>();
        updateWrapper.gt("sort", deletedSort)
                    .setSql("sort = sort - 1");
        
        // Thực hiện cập nhật hàng loạt và giảm giá trị sắp xếp của các bản ghi này đi 1
        this.update(updateWrapper);
    }

    @Override
    public Integer getNextAvailableSort() {
        // Truy vấn tất cả các giá trị sắp xếp hiện có và sắp xếp chúng theo thứ tự tăng dần
        List<Integer> sortValues = baseMapper.selectList(new QueryWrapper<AgentTemplateEntity>())
                .stream()
                .map(AgentTemplateEntity::getSort)
                .filter(Objects::nonNull)
                .sorted()
                .collect(Collectors.toList());
        
        // Nếu không có giá trị sắp xếp, trả về 1
        if (sortValues.isEmpty()) {
            return 1;
        }
        
        // Tìm số thứ tự nhỏ nhất chưa sử dụng
        int expectedSort = 1;
        for (Integer sort : sortValues) {
            if (sort > expectedSort) {
                // Tìm số sê-ri còn trống
                return expectedSort;
            }
            expectedSort = sort + 1;
        }
        
        // Nếu không còn chỗ trống thì trả về số thứ tự tối đa + 1
        return expectedSort;
    }
}
