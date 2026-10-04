package xiaozhi.modules.agent.service.biz.impl;

import java.util.Base64;
import java.util.Date;
import java.util.Objects;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import xiaozhi.common.constant.Constant;
import xiaozhi.common.redis.RedisKeys;
import xiaozhi.common.redis.RedisUtils;
import xiaozhi.modules.agent.dto.AgentChatHistoryReportDTO;
import xiaozhi.modules.agent.entity.AgentChatHistoryEntity;
import xiaozhi.modules.agent.entity.AgentEntity;
import xiaozhi.modules.agent.service.AgentChatAudioService;
import xiaozhi.modules.agent.service.AgentChatHistoryService;
import xiaozhi.modules.agent.service.AgentChatSummaryService;
import xiaozhi.modules.agent.service.AgentService;
import xiaozhi.modules.agent.service.biz.AgentChatHistoryBizService;
import xiaozhi.modules.device.entity.DeviceEntity;
import xiaozhi.modules.device.service.DeviceService;

/**
 * {@link AgentChatHistoryBizService} impl
 *
 * @author Goody
 * @version 1.0, 2025/4/30
 * @since 1.0.0
 */
@Service
@Slf4j
@RequiredArgsConstructor
public class AgentChatHistoryBizServiceImpl implements AgentChatHistoryBizService {
    private final AgentService agentService;
    private final AgentChatHistoryService agentChatHistoryService;
    private final AgentChatAudioService agentChatAudioService;
    private final AgentChatSummaryService agentChatSummaryService;
    private final RedisUtils redisUtils;
    private final DeviceService deviceService;

    /**
     * Xử lý báo cáo bản ghi trò chuyện, bao gồm tải tệp lên và bản ghi thông tin liên quan
     *
     * @param report Đối tượng đầu vào chứa thông tin cần thiết để báo cáo trò chuyện
     * @return Kết quả upload, true nghĩa là thành công, false nghĩa là thất bại
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public Boolean report(AgentChatHistoryReportDTO report) {
        String macAddress = report.getMacAddress();
        Byte chatType = report.getChatType();
        Long reportTimeMillis = null != report.getReportTime() ? report.getReportTime()
                : System.currentTimeMillis();
        log.info("小智设备聊天上报请求: macAddress={}, type={} reportTime={}", macAddress, chatType, reportTimeMillis);

        // Truy vấn tác nhân mặc định tương ứng dựa trên địa chỉ MAC của thiết bị để xác định xem có cần báo cáo hay không.
        AgentEntity agentEntity = agentService.getDefaultAgentByMacAddress(macAddress);
        if (agentEntity == null) {
            return Boolean.FALSE;
        }

        Integer chatHistoryConf = agentEntity.getChatHistoryConf();
        String agentId = agentEntity.getId();

        if (Objects.equals(chatHistoryConf, Constant.ChatHistoryConfEnum.RECORD_TEXT.getCode())) {
            saveChatText(report, agentId, macAddress, null, reportTimeMillis);
        } else if (Objects.equals(chatHistoryConf, Constant.ChatHistoryConfEnum.RECORD_TEXT_AUDIO.getCode())) {
            String audioId = saveChatAudio(report);
            saveChatText(report, agentId, macAddress, audioId, reportTimeMillis);
        }

        // Cập nhật thiết bị thời gian trò chuyện gần đây nhất
        redisUtils.set(RedisKeys.getAgentDeviceLastConnectedAtById(agentId), new Date());

        // Cập nhật thời gian kết nối cuối cùng của thiết bị
        DeviceEntity device = deviceService.getDeviceByMacAddress(macAddress);
        if (device != null) {
            deviceService.updateDeviceConnectionInfo(agentId, device.getId(), null);
        } else {
            log.warn("聊天记录上报时，未找到mac地址为 {} 的设备", macAddress);
        }

        return Boolean.TRUE;
    }

    /**
     * báo cáo giải mã base64.getOpusDataBase64(), được lưu trữ trong bảng ai_agent_chat_audio
     */
    private String saveChatAudio(AgentChatHistoryReportDTO report) {
        String audioId = null;

        if (report.getAudioBase64() != null && !report.getAudioBase64().isEmpty()) {
            try {
                byte[] audioData = Base64.getDecoder().decode(report.getAudioBase64());
                audioId = agentChatAudioService.saveAudio(audioData);
                log.info("音频数据保存成功，audioId={}", audioId);
            } catch (Exception e) {
                log.error("音频数据保存失败", e);
                return null;
            }
        }
        return audioId;
    }

    /**
     * Tập hợp dữ liệu báo cáo
     */
    private void saveChatText(AgentChatHistoryReportDTO report, String agentId, String macAddress, String audioId,
            Long reportTime) {
        // Xây dựng thực thể bản ghi trò chuyện
        AgentChatHistoryEntity entity = AgentChatHistoryEntity.builder()
                .macAddress(macAddress)
                .agentId(agentId)
                .sessionId(report.getSessionId())
                .chatType(report.getChatType())
                .content(report.getContent())
                .audioId(audioId)
                .createdAt(new Date(reportTime))
                // LƯU Ý(haotian): Không cần đặt cập nhật 26/5/2025, trọng tâm là createAt và bằng cách này, bạn có thể thấy độ trễ báo cáo
                .build();

        // lưu dữ liệu
        agentChatHistoryService.save(entity);

        log.info("设备 {} 对应智能体 {} 上报成功", macAddress, agentId);
    }
}
