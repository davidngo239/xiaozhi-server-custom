package xiaozhi.modules.agent.service.impl;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.apache.commons.lang3.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;

import lombok.RequiredArgsConstructor;
import xiaozhi.common.constant.Constant;
import xiaozhi.modules.agent.dto.AgentChatHistoryDTO;
import xiaozhi.modules.agent.dto.AgentChatSummaryDTO;
import xiaozhi.modules.agent.dto.AgentMemoryDTO;
import xiaozhi.modules.agent.dto.AgentUpdateDTO;
import xiaozhi.modules.agent.entity.AgentChatHistoryEntity;
import xiaozhi.modules.agent.service.AgentChatHistoryService;
import xiaozhi.modules.agent.service.AgentChatSummaryService;
import xiaozhi.modules.agent.service.AgentChatTitleService;
import xiaozhi.modules.agent.service.AgentService;
import xiaozhi.modules.agent.vo.AgentInfoVO;
import xiaozhi.modules.device.entity.DeviceEntity;
import xiaozhi.modules.device.service.DeviceService;
import xiaozhi.modules.llm.service.LLMService;
import xiaozhi.modules.model.entity.ModelConfigEntity;
import xiaozhi.modules.model.service.ModelConfigService;

/**
 * Lớp triển khai dịch vụ tóm tắt bản ghi cuộc trò chuyện của tổng đài viên
 * Triển khai logic tóm tắt trong mem_local_short.py ở phía Python
 */
@Service
@RequiredArgsConstructor
public class AgentChatSummaryServiceImpl implements AgentChatSummaryService {

    private static final Logger log = LoggerFactory.getLogger(AgentChatSummaryServiceImpl.class);

    private final AgentChatHistoryService agentChatHistoryService;
    private final AgentService agentService;
    private final AgentChatTitleService agentChatTitleService;
    private final DeviceService deviceService;
    private final LLMService llmService;
    private final ModelConfigService modelConfigService;

    // Hằng số quy tắc tóm tắt
    private static final int MAX_SUMMARY_LENGTH = 1800; // Độ dài tóm tắt tối đa
    private static final Pattern JSON_PATTERN = Pattern.compile("\\{.*?\\}", Pattern.DOTALL);
    private static final Pattern DEVICE_CONTROL_PATTERN = Pattern.compile("设备控制|设备操作|控制设备|设备状态",
            Pattern.CASE_INSENSITIVE);
    private static final Pattern WEATHER_PATTERN = Pattern.compile("天气|温度|湿度|降雨|气象", Pattern.CASE_INSENSITIVE);
    private static final Pattern DATE_PATTERN = Pattern.compile("日期|时间|星期|月份|年份", Pattern.CASE_INSENSITIVE);

    private AgentChatSummaryDTO generateChatSummary(String sessionId) {
        try {
            System.out.println("开始生成会话 " + sessionId + " 的聊天记录总结");

            // 1. Nhận bản ghi trò chuyện dựa trên sessionId
            List<AgentChatHistoryDTO> chatHistory = getChatHistoryBySessionId(sessionId);
            if (chatHistory == null || chatHistory.isEmpty()) {
                return new AgentChatSummaryDTO(sessionId, "未找到该会话的聊天记录");
            }

            // 2. Lấy thông tin đại lý
            String agentId = getAgentIdFromSession(sessionId, chatHistory);
            if (StringUtils.isBlank(agentId)) {
                return new AgentChatSummaryDTO(sessionId, "无法获取智能体信息");
            }

            // 3. Trích xuất nội dung hội thoại chính
            List<String> meaningfulMessages = extractMeaningfulMessages(chatHistory);
            if (meaningfulMessages.isEmpty()) {
                return new AgentChatSummaryDTO(sessionId, "没有有效的对话内容可总结");
            }

            // 4. Tạo bản tóm tắt (phương thức generateSummaryFromMessages đã chứa logic giới hạn độ dài)
            String summary = generateSummaryFromMessages(meaningfulMessages, agentId);

            log.info("成功生成会话 {} 的聊天记录总结，长度: {} 字符", sessionId, summary.length());
            return new AgentChatSummaryDTO(sessionId, agentId, summary);

        } catch (Exception e) {
            log.error("生成会话 {} 的聊天记录总结时发生错误: {}", sessionId, e.getMessage());
            return new AgentChatSummaryDTO(sessionId, "生成总结时发生错误: " + e.getMessage());
        }
    }

    @Override
    public boolean generateAndSaveChatSummary(String sessionId) {
        try {
            DeviceEntity device = getDeviceBySessionId(sessionId);
            if (device == null) {
                log.info("未找到与会话 {} 关联的设备", sessionId);
                return false;
            }

            String agentId = device.getAgentId();
            String memModelId = agentService.getAgentById(agentId).getMemModelId();

            if (memModelId == null || memModelId.equals(Constant.MEMORY_MEM_REPORT_ONLY)) {
                log.info("会话 {} 使用仅上报聊天记录模式，跳过记忆总结", sessionId);
                return true;
            }

            boolean shouldSummarizeMemory = !memModelId.equals(Constant.MEMORY_NO_MEM)
                    && !memModelId.equals(Constant.MEMORY_MEM0AI)
                    && !memModelId.equals(Constant.MEMORY_POWERMEM);

            if (shouldSummarizeMemory) {
                AgentChatSummaryDTO summaryDTO = generateChatSummary(sessionId);
                if (summaryDTO.isSuccess()) {
                    agentService.updateAgentById(agentId, new AgentUpdateDTO() {
                        {
                            setSummaryMemory(summaryDTO.getSummary());
                        }
                    }, false);
                    log.info("成功保存会话 {} 的聊天记录总结到智能体 {}", sessionId, agentId);
                } else {
                    log.info("生成总结失败: {}", summaryDTO.getErrorMessage());
                }
            } else {
                log.info("会话 {} 使用 {} 模式，跳过记忆总结", sessionId, memModelId);
            }

            return true;

        } catch (Exception e) {
            log.error("保存会话 {} 的聊天记录总结时发生错误: {}", sessionId, e.getMessage());
            return false;
        }
    }

    @Override
    public boolean generateAndSaveChatTitle(String sessionId) {
        try {
            // Tự động lấy AgentId
            String agentId = findAgentIdBySessionId(sessionId);
            if (StringUtils.isBlank(agentId)) {
                log.warn("会话 {} 无法获取智能体信息，跳过标题生成", sessionId);
                return false;
            }

            List<AgentChatHistoryDTO> chatHistory = getChatHistoryBySessionId(sessionId);
            if (chatHistory == null || chatHistory.isEmpty()) {
                return false;
            }

            List<String> meaningfulMessages = extractMeaningfulMessages(chatHistory);
            if (meaningfulMessages.isEmpty()) {
                return false;
            }

            StringBuilder conversation = new StringBuilder();
            for (int i = 0; i < meaningfulMessages.size(); i++) {
                conversation.append("消息").append(i + 1).append(": ").append(meaningfulMessages.get(i)).append("\n");
            }

            String slmModelId = getSlmModelId(agentId);
            String title = llmService.generateTitle(conversation.toString(), slmModelId);

            if (StringUtils.isNotBlank(title)) {
                agentChatTitleService.saveOrUpdateTitle(sessionId, title);
                log.info("成功保存会话 {} 的标题: {}", sessionId, title);
                return true;
            }
            return false;
        } catch (Exception e) {
            log.error("生成会话 {} 的标题时发生错误: {}", sessionId, e.getMessage());
            return false;
        }
    }

    private String getSlmModelId(String agentId) {
        try {
            if (StringUtils.isBlank(agentId)) {
                return null;
            }

            AgentInfoVO agentInfo = agentService.getAgentById(agentId);
            if (agentInfo == null) {
                return null;
            }

            String slmModelId = agentInfo.getSlmModelId();
            if (StringUtils.isNotBlank(slmModelId)) {
                log.info("会话 {} 使用SLM模型: {}", agentId, slmModelId);
                return slmModelId;
            }

            ModelConfigEntity defaultLlmConfig = getDefaultLLMConfig();
            if (defaultLlmConfig != null) {
                log.info("会话 {} 使用默认LLM模型: {}", agentId, defaultLlmConfig.getId());
                return defaultLlmConfig.getId();
            }

            String llmModelId = agentInfo.getLlmModelId();
            log.info("会话 {} 使用LLM模型(最终回退): {}", agentId, llmModelId);
            return llmModelId;
        } catch (Exception e) {
            log.error("获取智能体slm模型ID失败，agentId: {}, 错误: {}", agentId, e.getMessage());
            return null;
        }
    }

    private ModelConfigEntity getDefaultLLMConfig() {
        try {
            List<ModelConfigEntity> llmConfigs = modelConfigService.getEnabledModelsByType("LLM");
            if (llmConfigs == null || llmConfigs.isEmpty()) {
                return null;
            }

            for (ModelConfigEntity config : llmConfigs) {
                if (config.getIsDefault() != null && config.getIsDefault() == 1) {
                    return config;
                }
            }

            return llmConfigs.get(0);
        } catch (Exception e) {
            log.error("获取默认LLM配置失败: {}", e.getMessage());
            return null;
        }
    }

    /**
     * Nhận lịch sử trò chuyện dựa trên ID phiên
     */
    private List<AgentChatHistoryDTO> getChatHistoryBySessionId(String sessionId) {
        try {
            // Tại đây bạn cần lấy bản ghi trò chuyện dựa trên sessionId
            // Vì giao diện hiện tại yêu cầu ID tác nhân nên trước tiên chúng ta cần tìm ID tác nhân được liên kết
            String agentId = findAgentIdBySessionId(sessionId);
            if (StringUtils.isBlank(agentId)) {
                return null;
            }
            return agentChatHistoryService.getChatHistoryBySessionId(agentId, sessionId);
        } catch (Exception e) {
            log.error("获取会话 {} 的聊天记录失败: {}", sessionId, e.getMessage());
            return null;
        }
    }

    /**
     * Tìm ID tác nhân được liên kết dựa trên ID phiên
     */
    private String findAgentIdBySessionId(String sessionId) {
        try {
            // Truy vấn bản ghi đầu tiên của phiên để lấy AgentId
            QueryWrapper<AgentChatHistoryEntity> wrapper = new QueryWrapper<>();
            wrapper.select("agent_id")
                    .eq("session_id", sessionId)
                    .last("LIMIT 1");

            AgentChatHistoryEntity entity = agentChatHistoryService.getOne(wrapper);
            return entity != null ? entity.getAgentId() : null;
        } catch (Exception e) {
            log.error("根据会话ID {} 查找智能体ID失败: {}", sessionId, e.getMessage());
            return null;
        }
    }

    /**
     * Nhận ID đại lý từ phiên
     */
    private String getAgentIdFromSession(String sessionId, List<AgentChatHistoryDTO> chatHistory) {
        // Truy vấn ID đại lý trực tiếp từ cơ sở dữ liệu
        return findAgentIdBySessionId(sessionId);
    }

    /**
     * Trích xuất nội dung hội thoại có ý nghĩa (chỉ trích xuất tin nhắn của người dùng, loại trừ phản hồi của AI)
     */
    private List<String> extractMeaningfulMessages(List<AgentChatHistoryDTO> chatHistory) {
        List<String> meaningfulMessages = new ArrayList<>();

        for (AgentChatHistoryDTO message : chatHistory) {
            // Chỉ xử lý tin nhắn của người dùng (chatType = 1)
            if (message.getChatType() != null && message.getChatType() == 1) {
                String content = extractContentFromMessage(message);
                if (isMeaningfulMessage(content)) {
                    meaningfulMessages.add(content);
                }
            }
        }

        return meaningfulMessages;
    }

    /**
     * Trích xuất nội dung từ tin nhắn (xử lý định dạng JSON)
     */
    private String extractContentFromMessage(AgentChatHistoryDTO message) {
        String content = message.getContent();
        if (StringUtils.isBlank(content)) {
            return "";
        }

        // Xử lý nội dung có định dạng JSON (nhất quán về mặt logic với giao diện ChatHistoryDialog.vue)
        Matcher matcher = JSON_PATTERN.matcher(content);
        if (matcher.find()) {
            String jsonContent = matcher.group();
            // Xử lý đơn giản: trích xuất nội dung văn bản trong JSON
            return extractTextFromJson(jsonContent);
        }

        return content;
    }

    /**
     * Trích xuất nội dung văn bản từ JSON
     */
    private String extractTextFromJson(String jsonContent) {
        // Xử lý đơn giản: trích xuất giá trị của trường "nội dung"
        Pattern contentPattern = Pattern.compile("\"content\"\s*:\s*\"([^\"]*)\"");
        Matcher matcher = contentPattern.matcher(jsonContent);
        if (matcher.find()) {
            return matcher.group(1);
        }
        return jsonContent;
    }

    /**
     * Xác định xem tin nhắn có ý nghĩa hay không
     */
    private boolean isMeaningfulMessage(String content) {
        if (StringUtils.isBlank(content)) {
            return false;
        }

        // Loại trừ thông tin điều khiển thiết bị
        if (DEVICE_CONTROL_PATTERN.matcher(content).find()) {
            return false;
        }

        // Loại trừ nội dung không liên quan như ngày tháng, thời tiết, v.v.
        if (WEATHER_PATTERN.matcher(content).find() || DATE_PATTERN.matcher(content).find()) {
            return false;
        }

        // Loại trừ những tin nhắn quá ngắn
        return content.length() >= 5;
    }

    /**
     * Tạo bản tóm tắt từ tin nhắn
     */
    private String generateSummaryFromMessages(List<String> messages, String agentId) {
        if (messages.isEmpty()) {
            return "本次对话内容较少，没有需要总结的重要信息。";
        }

        // Xây dựng một cuộc trò chuyện hoàn chỉnh
        StringBuilder conversation = new StringBuilder();
        for (int i = 0; i < messages.size(); i++) {
            conversation.append("消息").append(i + 1).append(": ").append(messages.get(i)).append("\n");
        }

        try {
            // Lấy ký ức lịch sử của đại lý hiện tại
            String historyMemory = getCurrentAgentMemory(agentId);

            // Gọi dịch vụ LLM để tóm tắt thông minh, chuyển AgentId để có cấu hình mô hình chính xác
            String summary = callJavaLLMForSummaryWithHistory(conversation.toString(), historyMemory, agentId);

            // Áp dụng quy tắc tóm tắt: giới hạn độ dài tối đa
            if (summary.length() > MAX_SUMMARY_LENGTH) {
                summary = summary.substring(0, MAX_SUMMARY_LENGTH) + "...";
            }

            return summary;
        } catch (Exception e) {
            log.error("调用Java端LLM服务失败: {}", e.getMessage());
            throw new RuntimeException("LLM服务不可用，无法生成聊天总结");
        }
    }

    /**
     * Lấy ký ức lịch sử của đại lý hiện tại
     */
    private String getCurrentAgentMemory(String agentId) {
        try {
            if (StringUtils.isBlank(agentId)) {
                return null;
            }

            // Nhận thông tin đại lý
            AgentInfoVO agentInfo = agentService.getAgentById(agentId);
            if (agentInfo == null) {
                return null;
            }

            // Trả về bộ nhớ tóm tắt hiện tại của tác nhân
            return agentInfo.getSummaryMemory();
        } catch (Exception e) {
            log.error("获取智能体历史记忆失败，agentId: {}, 错误: {}", agentId, e.getMessage());
            return null;
        }
    }

    /**
     * Gọi dịch vụ LLM phía Java để có bản tóm tắt thông minh (hỗ trợ hợp nhất bộ nhớ lịch sử)
     */
    private String callJavaLLMForSummaryWithHistory(String conversation, String historyMemory, String agentId) {
        try {
            String modelId = getSlmModelId(agentId);

            if (StringUtils.isBlank(modelId)) {
                log.info("未找到SLM模型，使用默认LLM服务");
                return llmService.generateSummaryWithHistory(conversation, historyMemory, null, null);
            }

            String summary = llmService.generateSummaryWithHistory(conversation, historyMemory, null, modelId);

            if (StringUtils.isNotBlank(summary) && !summary.equals("服务暂不可用") && !summary.equals("总结生成失败")) {
                return summary;
            }

            throw new RuntimeException("Java端LLM服务返回异常: " + summary);

        } catch (Exception e) {
            log.error("调用Java端LLM服务异常，agentId: {}, 错误: {}", agentId, e.getMessage());
            throw e;
        }
    }

    /**
     * Gọi dịch vụ LLM phía Java để có bản tóm tắt thông minh
     */
    private String callJavaLLMForSummary(String conversation, String agentId) {
        try {
            String modelId = getSlmModelId(agentId);

            if (StringUtils.isBlank(modelId)) {
                log.info("未找到SLM模型，使用默认LLM服务");
                return llmService.generateSummary(conversation);
            }

            String summary = llmService.generateSummaryWithModel(conversation, modelId);

            if (StringUtils.isNotBlank(summary) && !summary.equals("服务暂不可用") && !summary.equals("总结生成失败")) {
                return summary;
            }

            throw new RuntimeException("Java端LLM服务返回异常: " + summary);

        } catch (Exception e) {
            log.error("调用Java端LLM服务异常，agentId: {}, 错误: {}", agentId, e.getMessage());
            throw e;
        }
    }

    /**
     * Lấy ID mô hình LLM của bản tóm tắt bộ nhớ
     */
    private String getMemorySummaryModelId(String agentId) {
        try {
            if (StringUtils.isBlank(agentId)) {
                return null;
            }

            // Nhận thông tin đại lý
            AgentInfoVO agentInfo = agentService.getAgentById(agentId);
            if (agentInfo == null) {
                return null;
            }

            // Lấy ID mô hình bộ nhớ của tác nhân
            String memModelId = agentInfo.getMemModelId();
            if (StringUtils.isBlank(memModelId)) {
                return null;
            }

            // Nhận cấu hình mô hình bộ nhớ
            ModelConfigEntity memModelConfig = modelConfigService.getModelByIdFromCache(memModelId);
            if (memModelConfig == null || memModelConfig.getConfigJson() == null) {
                return null;
            }

            // Trích xuất ID mô hình LLM tương ứng từ cấu hình mô hình bộ nhớ
            Map<String, Object> configMap = memModelConfig.getConfigJson();
            String llmModelId = (String) configMap.get("llm");

            if (StringUtils.isBlank(llmModelId)) {
                // Nếu mô hình bộ nhớ không được định cấu hình bằng LLM riêng thì mô hình LLM mặc định của tác nhân sẽ được sử dụng.
                return agentInfo.getLlmModelId();
            }

            return llmModelId;
        } catch (Exception e) {
            log.error("获取记忆总结LLM模型ID失败，agentId: {}, 错误: {}", agentId, e.getMessage());
            return null;
        }
    }

    /**
     * Nhận thông tin thiết bị dựa trên ID phiên
     */
    private DeviceEntity getDeviceBySessionId(String sessionId) {
        try {
            // Truy vấn bản ghi đầu tiên của phiên để lấy macAddress
            QueryWrapper<AgentChatHistoryEntity> wrapper = new QueryWrapper<>();
            wrapper.select("mac_address")
                    .eq("session_id", sessionId)
                    .last("LIMIT 1");

            AgentChatHistoryEntity entity = agentChatHistoryService.getOne(wrapper);
            if (entity != null && StringUtils.isNotBlank(entity.getMacAddress())) {
                return deviceService.getDeviceByMacAddress(entity.getMacAddress());
            }
            return null;
        } catch (Exception e) {
            log.error("根据会话ID {} 查找设备信息失败: {}", sessionId, e.getMessage());
            return null;
        }
    }
}
