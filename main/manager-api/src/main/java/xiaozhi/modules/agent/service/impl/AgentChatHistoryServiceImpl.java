package xiaozhi.modules.agent.service.impl;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import cn.hutool.core.collection.CollUtil;
import cn.hutool.core.collection.ListUtil;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.spring.repository.CrudRepository;

import xiaozhi.common.constant.Constant;
import xiaozhi.common.page.PageData;
import xiaozhi.common.utils.ConvertUtils;
import xiaozhi.common.utils.JsonUtils;
import xiaozhi.modules.agent.Enums.AgentChatHistoryType;
import xiaozhi.modules.agent.dao.AiAgentChatHistoryDao;
import xiaozhi.modules.agent.dto.AgentChatHistoryDTO;
import xiaozhi.modules.agent.dto.AgentChatSessionDTO;
import xiaozhi.modules.agent.entity.AgentChatHistoryEntity;
import xiaozhi.modules.agent.service.AgentChatHistoryService;
import xiaozhi.modules.agent.service.AgentChatTitleService;
import xiaozhi.modules.agent.vo.AgentChatHistoryUserVO;

/**
 * Dịch vụ xử lý bảng ghi cuộc trò chuyện của đại lý {@link AgentChatHistoryService} được áp dụng
 *
 * @author Goody
 * @version 1.0, 2025/4/30
 * @since 1.0.0
 */
@Service
@RequiredArgsConstructor
public class AgentChatHistoryServiceImpl extends CrudRepository<AiAgentChatHistoryDao, AgentChatHistoryEntity>
        implements AgentChatHistoryService {

    private final AgentChatTitleService agentChatTitleService;

    @Override
    public PageData<AgentChatSessionDTO> getSessionListByAgentId(Map<String, Object> params) {
        String agentId = (String) params.get("agentId");
        int page = Integer.parseInt(params.get(Constant.PAGE).toString());
        int limit = Integer.parseInt(params.get(Constant.LIMIT).toString());

        // Xây dựng điều kiện truy vấn
        QueryWrapper<AgentChatHistoryEntity> wrapper = new QueryWrapper<>();
        wrapper.select("session_id", "MAX(created_at) as created_at", "COUNT(*) as chat_count")
                .eq("agent_id", agentId)
                .groupBy("session_id")
                .orderByDesc("created_at");

        // Thực hiện truy vấn phân trang
        Page<Map<String, Object>> pageParam = new Page<>(page, limit);
        IPage<Map<String, Object>> result = this.baseMapper.selectMapsPage(pageParam, wrapper);

        List<AgentChatSessionDTO> records = result.getRecords().stream().map(map -> {
            AgentChatSessionDTO dto = new AgentChatSessionDTO();
            dto.setSessionId((String) map.get("session_id"));
            dto.setCreatedAt((LocalDateTime) map.get("created_at"));
            dto.setChatCount(((Number) map.get("chat_count")).intValue());
            dto.setTitle(agentChatTitleService.getTitleBySessionId(dto.getSessionId()));
            return dto;
        }).collect(Collectors.toList());

        return new PageData<>(records, result.getTotal());
    }

    @Override
    public List<AgentChatHistoryDTO> getChatHistoryBySessionId(String agentId, String sessionId) {
        // Xây dựng điều kiện truy vấn
        QueryWrapper<AgentChatHistoryEntity> wrapper = new QueryWrapper<>();
        wrapper.eq("agent_id", agentId)
                .eq("session_id", sessionId)
                .orderByAsc("created_at");

        // Truy vấn lịch sử trò chuyện
        List<AgentChatHistoryEntity> historyList = list(wrapper);

        // Chuyển đổi sang DTO
        return ConvertUtils.sourceToTarget(historyList, AgentChatHistoryDTO.class);
    }

    @Override
    public String getAgentIdBySessionId(String sessionId) {
        if (sessionId == null || sessionId.isBlank()) {
            return null;
        }
        AgentChatHistoryEntity entity = baseMapper.selectOne(
                new LambdaQueryWrapper<AgentChatHistoryEntity>()
                        .select(AgentChatHistoryEntity::getAgentId)
                        .eq(AgentChatHistoryEntity::getSessionId, sessionId)
                        .last("LIMIT 1"));
        return entity == null ? null : entity.getAgentId();
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deleteByAgentId(String agentId, Boolean deleteAudio, Boolean deleteText) {
        if (deleteAudio) {
            // Xóa âm thanh theo đợt để tránh hết thời gian chờ
            List<String> audioIds = baseMapper.getAudioIdsByAgentId(agentId);
            if (CollUtil.isNotEmpty(audioIds)) {
                // Xóa 1000 mục trong mỗi đợt
                List<List<String>> batch = ListUtil.split(audioIds, 1000);
                batch.forEach(dataList -> {
                    baseMapper.deleteAudioByIds(dataList);
                });
            }
        }
        if (deleteAudio && !deleteText) {
            baseMapper.deleteAudioIdByAgentId(agentId);
        }
        if (deleteText) {
            baseMapper.deleteHistoryByAgentId(agentId);
        }

    }

    @Override
    public List<AgentChatHistoryUserVO> getRecentlyFiftyByAgentId(String agentId) {
        // Xây dựng điều kiện truy vấn (không thêm, sắp xếp theo thời gian tạo, dữ liệu vốn đã lớn hơn khi có khóa chính và lớn hơn theo thời gian tạo)
        // Không thêm phần này có thể giảm chi phí sắp xếp tất cả dữ liệu trong quá trình quét phân trang toàn bộ đĩa)
        LambdaQueryWrapper<AgentChatHistoryEntity> wrapper = new LambdaQueryWrapper<>();
        wrapper.select(AgentChatHistoryEntity::getContent, AgentChatHistoryEntity::getAudioId)
                .eq(AgentChatHistoryEntity::getAgentId, agentId)
                .eq(AgentChatHistoryEntity::getChatType, AgentChatHistoryType.USER.getValue())
                .isNotNull(AgentChatHistoryEntity::getAudioId)
                // Thêm dòng này để đảm bảo rằng kết quả truy vấn được sắp xếp theo thứ tự giảm dần theo thời gian tạo
                // Lý do sử dụng id: Ở định dạng dữ liệu, id càng lớn thì thời gian tạo càng muộn nên kết quả sử dụng id cũng giống như kết quả của việc sắp xếp thời gian tạo theo thứ tự giảm dần.
                // Ưu điểm của id theo thứ tự giảm dần là nó có hiệu suất cao và có chỉ mục khóa chính. Không cần phải thực hiện quét loại trừ và so sánh lại trong quá trình sắp xếp.
                .orderByDesc(AgentChatHistoryEntity::getId);

        // Xây dựng truy vấn phân trang để truy vấn 50 trang dữ liệu đầu tiên
        Page<AgentChatHistoryEntity> pageParam = new Page<>(0, 50);
        IPage<AgentChatHistoryEntity> result = this.baseMapper.selectPage(pageParam, wrapper);
        return result.getRecords().stream().map(item -> {
            AgentChatHistoryUserVO vo = ConvertUtils.sourceToTarget(item, AgentChatHistoryUserVO.class);
            // Xử lý trường nội dung để đảm bảo chỉ trả về nội dung trò chuyện
            if (vo != null && vo.getContent() != null) {
                vo.setContent(extractContentFromString(vo.getContent()));
            }
            return vo;
        }).toList();
    }

    /**
     * Trích xuất nội dung trò chuyện từ trường nội dung
     * Nếu nội dung ở định dạng JSON (chẳng hạn như {"loa": "Người nói không xác định", "nội dung": "Bây giờ là mấy giờ."}), hãy trích xuất nội dung
     * trường
     * Nếu nội dung là một chuỗi thông thường, hãy trả lại trực tiếp
     * 
     * @param content dung nội dung gốc
     * @return nội dung trò chuyện được trích xuất
     */
    private String extractContentFromString(String content) {
        if (content == null || content.trim().isEmpty()) {
            return content;
        }

        // Hãy thử phân tích thành JSON
        try {
            Map<String, Object> jsonMap = JsonUtils.parseMap(content);
            if (jsonMap != null && jsonMap.containsKey("content")) {
                Object contentObj = jsonMap.get("content");
                return contentObj != null ? contentObj.toString() : content;
            }
        } catch (Exception e) {
            // Nếu nó không phải là JSON hợp lệ, hãy trả lại trực tiếp nội dung gốc.
        }

        // Nếu nó không ở định dạng JSON hoặc không có trường nội dung thì nội dung gốc sẽ được trả về trực tiếp.
        return content;
    }

    @Override
    public String getContentByAudioId(String audioId) {
        AgentChatHistoryEntity agentChatHistoryEntity = baseMapper
                .selectOne(new LambdaQueryWrapper<AgentChatHistoryEntity>()
                        .select(AgentChatHistoryEntity::getContent)
                        .eq(AgentChatHistoryEntity::getAudioId, audioId));
        return agentChatHistoryEntity == null ? null : agentChatHistoryEntity.getContent();
    }

    @Override
    public String getAgentIdByAudioId(String audioId) {
        if (audioId == null || audioId.isBlank()) {
            return null;
        }
        AgentChatHistoryEntity entity = baseMapper.selectOne(
                new LambdaQueryWrapper<AgentChatHistoryEntity>()
                        .select(AgentChatHistoryEntity::getAgentId)
                        .eq(AgentChatHistoryEntity::getAudioId, audioId)
                        .last("LIMIT 1"));
        return entity == null ? null : entity.getAgentId();
    }

    @Override
    public boolean isAudioOwnedByAgent(String audioId, String agentId) {
        // Truy vấn xem có dữ liệu chỉ định id âm thanh và id tác nhân hay không. Nếu có và chỉ có một mô tả về thuộc tính dữ liệu này, tác nhân này
        Long row = baseMapper.selectCount(new LambdaQueryWrapper<AgentChatHistoryEntity>()
                .eq(AgentChatHistoryEntity::getAudioId, audioId)
                .eq(AgentChatHistoryEntity::getAgentId, agentId));
        return row == 1;
    }
}
