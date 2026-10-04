package xiaozhi.modules.agent.controller;

import java.io.IOException;
import java.io.OutputStream;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import org.apache.commons.lang3.StringUtils;
import org.apache.shiro.authz.annotation.RequiresPermissions;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import xiaozhi.common.constant.Constant;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.page.PageData;
import xiaozhi.common.redis.RedisKeys;
import xiaozhi.common.redis.RedisUtils;
import xiaozhi.common.user.UserDetail;
import xiaozhi.common.utils.DateUtils;
import xiaozhi.common.utils.MessageUtils;
import xiaozhi.common.utils.Result;
import xiaozhi.modules.agent.dto.AgentChatHistoryDTO;
import xiaozhi.modules.agent.dto.AgentChatHistoryReportDTO;
import xiaozhi.modules.agent.dto.AgentChatSessionDTO;
import xiaozhi.modules.agent.service.AgentChatHistoryService;
import xiaozhi.modules.agent.service.AgentService;
import xiaozhi.modules.agent.service.biz.AgentChatHistoryBizService;
import xiaozhi.modules.security.user.SecurityUser;

@Tag(name = "智能体聊天历史管理")
@RequiredArgsConstructor
@RestController
@RequestMapping("/agent/chat-history")
public class AgentChatHistoryController {
    private final AgentChatHistoryBizService agentChatHistoryBizService;
    private final AgentChatHistoryService agentChatHistoryService;
    private final AgentService agentService;
    private final RedisUtils redisUtils;

    /**
     * Yêu cầu báo cáo trò chuyện dịch vụ Xiaozhi
     * <p>
     * Yêu cầu báo cáo trò chuyện dịch vụ Xiaozhi chứa dữ liệu âm thanh được mã hóa Base64 và thông tin liên quan.
     *
     * @param request tượng yêu cầu yêu cầu chứa các tệp đã tải lên và thông tin liên quan
     */
    @Operation(summary = "小智服务聊天上报请求")
    @PostMapping("/report")
    public Result<Boolean> uploadFile(@Valid @RequestBody AgentChatHistoryReportDTO request) {
        Boolean result = agentChatHistoryBizService.report(request);
        return new Result<Boolean>().ok(result);
    }

    /**
     * Nhận liên kết tải xuống lịch sử trò chuyện
     * 
     * @param agentId đại lý ID đại lý
     * @param sessionId ID phiên
     * @return UUID làm mã định danh tải xuống
     */
    @Operation(summary = "获取聊天记录下载链接")
    @RequiresPermissions("sys:role:normal")
    @PostMapping("/getDownloadUrl/{agentId}/{sessionId}")
    public Result<String> getDownloadUrl(@PathVariable("agentId") String agentId,
            @PathVariable("sessionId") String sessionId) {
        // Nhận người dùng hiện tại
        UserDetail user = SecurityUser.getUser();
        // Kiểm tra quyền
        if (!agentService.checkAgentPermission(agentId, user.getId())) {
            throw new RenException(ErrorCode.CHAT_HISTORY_NO_PERMISSION);
        }

        // Tạo UUID
        String uuid = UUID.randomUUID().toString();
        // Lưu trữ AgentId và sessionId trong Redis ở định dạng AgentId:sessionId
        redisUtils.set(RedisKeys.getChatHistoryKey(uuid), agentId + ":" + sessionId);

        return new Result<String>().ok(uuid);
    }

    /**
     * Tải xuống bản ghi cuộc trò chuyện của phiên này
     * 
     * @param uuid mã định danh tải xuống
     * @param response Phản hồi HTTP
     */
    @Operation(summary = "下载本会话聊天记录")
    @GetMapping("/download/{uuid}/current")
    public void downloadCurrentSession(@PathVariable("uuid") String uuid,
            HttpServletResponse response) {
        // Nhận AgentId và sessionId từ Redis
        String agentSessionInfo = (String) redisUtils.get(RedisKeys.getChatHistoryKey(uuid));
        if (StringUtils.isBlank(agentSessionInfo)) {
            throw new RenException(ErrorCode.DOWNLOAD_LINK_EXPIRED);
        }

        try {
            // Phân tích tác nhânId và sessionId
            String[] parts = agentSessionInfo.split(":");
            if (parts.length != 2) {
                throw new RenException(ErrorCode.DOWNLOAD_LINK_INVALID);
            }
            String agentId = parts[0];
            String sessionId = parts[1];

            // Thực hiện tải xuống
            downloadChatHistory(agentId, List.of(sessionId), response);
        } finally {
            // Xóa UUID sau khi tải xuống hoàn tất để tránh bị đánh cắp.
            redisUtils.delete(RedisKeys.getChatHistoryKey(uuid));
        }
    }

    /**
     * Tải xuống bản ghi trò chuyện của cuộc trò chuyện này và 20 cuộc trò chuyện trước đó
     * 
     * @param uuid mã định danh tải xuống
     * @param response Phản hồi HTTP
     */
    @Operation(summary = "下载本会话及前20条会话聊天记录")
    @GetMapping("/download/{uuid}/previous")
    public void downloadCurrentSessionWithPrevious(@PathVariable("uuid") String uuid,
            HttpServletResponse response) {
        // Nhận AgentId và sessionId từ Redis
        String agentSessionInfo = (String) redisUtils.get(RedisKeys.getChatHistoryKey(uuid));
        if (StringUtils.isBlank(agentSessionInfo)) {
            throw new RenException(ErrorCode.DOWNLOAD_LINK_EXPIRED);
        }

        try {
            // Phân tích tác nhânId và sessionId
            String[] parts = agentSessionInfo.split(":");
            if (parts.length != 2) {
                throw new RenException(ErrorCode.DOWNLOAD_LINK_INVALID);
            }
            String agentId = parts[0];
            String sessionId = parts[1];

            // Nhận danh sách tất cả các phiên
            Map<String, Object> params = Map.of(
                    "agentId", agentId,
                    Constant.PAGE, 1,
                    Constant.LIMIT, 1000 // Nhận đủ phiên
            );
            PageData<AgentChatSessionDTO> sessionPage = agentChatHistoryService.getSessionListByAgentId(params);
            List<AgentChatSessionDTO> allSessions = sessionPage.getList();

            // Tìm vị trí của phiên hiện tại trong danh sách
            int currentIndex = -1;
            for (int i = 0; i < allSessions.size(); i++) {
                if (allSessions.get(i).getSessionId().equals(sessionId)) {
                    currentIndex = i;
                    break;
                }
            }

            // Nếu tìm thấy phiên hiện tại, hãy thu thập phiên hiện tại và 20 ID phiên trước đó
            List<String> sessionIdsToDownload = new ArrayList<>();
            if (currentIndex != -1) {
                // Bắt đầu từ phiên hiện tại, tìm nạp ngược tối đa 20 phiên (phía sau mảng) (bao gồm cả phiên hiện tại)
                int endIndex = Math.min(allSessions.size() - 1, currentIndex + 20); // Đảm bảo không vượt qua ranh giới
                for (int i = currentIndex; i <= endIndex; i++) {
                    sessionIdsToDownload.add(allSessions.get(i).getSessionId());
                }
            }

            // Nếu không tìm thấy phiên hiện tại, ít nhất hãy tải xuống phiên hiện tại
            if (sessionIdsToDownload.isEmpty()) {
                sessionIdsToDownload.add(sessionId);
            }
            downloadChatHistory(agentId, sessionIdsToDownload, response);
        } finally {
            // Xóa UUID sau khi tải xuống hoàn tất để tránh bị đánh cắp.
            redisUtils.delete(RedisKeys.getChatHistoryKey(uuid));
        }
    }

    /**
     * Tải xuống lịch sử trò chuyện của một phiên được chỉ định
     * 
     * @param agentId đại lý ID đại lý
     * @param sessionIds danh sách ID phiên
     * @param response Phản hồi HTTP
     */
    private void downloadChatHistory(String agentId, List<String> sessionIds, HttpServletResponse response) {
        try {
            // Đặt tiêu đề phản hồi
            response.setContentType("text/plain;charset=UTF-8");
            String fileName = URLEncoder.encode("history.txt", StandardCharsets.UTF_8.toString());
            response.setHeader("Content-Disposition", "attachment;filename=" + fileName);

            // Nhận lịch sử trò chuyện và ghi vào luồng phản hồi
            try (OutputStream out = response.getOutputStream()) {
                // Tạo bản ghi cuộc trò chuyện cho mỗi cuộc trò chuyện
                for (String sessionId : sessionIds) {
                    // Nhận tất cả lịch sử trò chuyện của cuộc trò chuyện này
                    List<AgentChatHistoryDTO> chatHistoryList = agentChatHistoryService
                            .getChatHistoryBySessionId(agentId, sessionId);

                    // Lấy thời gian tạo tin nhắn đầu tiên từ lịch sử trò chuyện làm thời gian phiên
                    if (!chatHistoryList.isEmpty()) {
                        Date firstMessageTime = chatHistoryList.get(0).getCreatedAt();
                        String sessionTimeStr = DateUtils.format(firstMessageTime, DateUtils.DATE_TIME_PATTERN);
                        out.write((sessionTimeStr + "\n").getBytes(StandardCharsets.UTF_8));
                    }

                    for (AgentChatHistoryDTO message : chatHistoryList) {
                        String role = message.getChatType() == 1 ? MessageUtils.getMessage(ErrorCode.CHAT_ROLE_USER)
                                : MessageUtils.getMessage(ErrorCode.CHAT_ROLE_AGENT);
                        String direction = message.getChatType() == 1 ? ">>" : "<<";
                        Date messageTime = message.getCreatedAt();
                        String messageTimeStr = DateUtils.format(messageTime, DateUtils.DATE_TIME_PATTERN);
                        String content = message.getContent();

                        String line = "[" + role + "]-[" + messageTimeStr + "]" + direction + ":" + content + "\n";
                        out.write(line.getBytes(StandardCharsets.UTF_8));
                    }

                    // Thêm dòng trống vào các phiên riêng biệt
                    if (sessionIds.indexOf(sessionId) < sessionIds.size() - 1) {
                        out.write("\n".getBytes(StandardCharsets.UTF_8));
                    }
                }

                out.flush();
            }
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
}
