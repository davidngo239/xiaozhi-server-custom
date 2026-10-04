package xiaozhi.modules.agent.service.impl;

import java.net.URI;
import java.net.URISyntaxException;
import java.util.List;
import java.util.concurrent.Executor;
import java.util.stream.Collectors;

import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionTemplate;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestTemplate;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.spring.repository.CrudRepository;

import lombok.extern.slf4j.Slf4j;
import xiaozhi.common.constant.Constant;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.utils.ConvertUtils;
import xiaozhi.common.utils.JsonUtils;
import xiaozhi.modules.agent.dao.AgentVoicePrintDao;
import xiaozhi.modules.agent.dto.AgentVoicePrintSaveDTO;
import xiaozhi.modules.agent.dto.AgentVoicePrintUpdateDTO;
import xiaozhi.modules.agent.dto.IdentifyVoicePrintResponse;
import xiaozhi.modules.agent.entity.AgentVoicePrintEntity;
import xiaozhi.modules.agent.service.AgentChatAudioService;
import xiaozhi.modules.agent.service.AgentChatHistoryService;
import xiaozhi.modules.agent.service.AgentVoicePrintService;
import xiaozhi.modules.agent.vo.AgentVoicePrintVO;
import xiaozhi.modules.sys.service.SysParamsService;

/**
 * @author zjy
 */
@Service
@Slf4j
public class AgentVoicePrintServiceImpl extends CrudRepository<AgentVoicePrintDao, AgentVoicePrintEntity>
        implements AgentVoicePrintService {
    private final AgentChatAudioService agentChatAudioService;
    private final RestTemplate restTemplate;
    private final SysParamsService sysParamsService;
    private final AgentChatHistoryService agentChatHistoryService;
    // Lập trình các lớp giao dịch được cung cấp bởi Springboot
    private final TransactionTemplate transactionTemplate;
    // Sự công nhận
    private final Double RECOGNITION = 0.5;
    private final Executor taskExecutor;

    public AgentVoicePrintServiceImpl(AgentChatAudioService agentChatAudioService, RestTemplate restTemplate,
                                      SysParamsService sysParamsService, AgentChatHistoryService agentChatHistoryService,
                                      TransactionTemplate transactionTemplate, @Qualifier("taskExecutor") Executor taskExecutor) {
        this.agentChatAudioService = agentChatAudioService;
        this.restTemplate = restTemplate;
        this.sysParamsService = sysParamsService;
        this.agentChatHistoryService = agentChatHistoryService;
        this.transactionTemplate = transactionTemplate;
        this.taskExecutor = taskExecutor;
    }

    @Override
    public boolean insert(AgentVoicePrintSaveDTO dto) {
        // Nhận dữ liệu âm thanh
        ByteArrayResource resource = getVoicePrintAudioWAV(dto.getAgentId(), dto.getAudioId());
        // Kiểm tra xem giọng nói này đã được đăng ký chưa
        IdentifyVoicePrintResponse response = identifyVoicePrint(dto.getAgentId(), resource);
        if (response != null && response.getScore() > RECOGNITION) {
            // Truy vấn thông tin người dùng tương ứng dựa trên ID giọng nói được nhận dạng
            AgentVoicePrintEntity existingVoicePrint = baseMapper.selectById(response.getSpeakerId());
            String existingUserName = existingVoicePrint != null ? existingVoicePrint.getSourceName() : "未知用户";
            throw new RenException(ErrorCode.VOICEPRINT_ALREADY_REGISTERED, existingUserName);
        }
        AgentVoicePrintEntity entity = ConvertUtils.sourceToTarget(dto, AgentVoicePrintEntity.class);
        // Mở giao dịch
        return Boolean.TRUE.equals(transactionTemplate.execute(status -> {
            try {
                // Lưu thông tin giọng nói
                int row = baseMapper.insert(entity);
                // Chèn một phần dữ liệu. Nếu dữ liệu bị ảnh hưởng không bằng 1, điều đó có nghĩa là đã xảy ra sự cố. Lưu vấn đề và cuộn nó lại.
                if (row != 1) {
                    status.setRollbackOnly(); // Đánh dấu giao dịch để khôi phục
                    return false;
                }
                // Gửi yêu cầu đăng ký giọng nói
                registerVoicePrint(entity.getId(), resource);
                return true;
            } catch (RenException e) {
                status.setRollbackOnly(); // Đánh dấu giao dịch để khôi phục
                throw e;
            } catch (Exception e) {
                status.setRollbackOnly(); // Đánh dấu giao dịch để khôi phục
                log.error("保存声纹错误原因：{}", e.getMessage());
                throw new RenException(ErrorCode.VOICE_PRINT_SAVE_ERROR);
            }
        }));
    }

    @Override
    public boolean delete(Long userId, String voicePrintId) {
        // Mở giao dịch
        boolean b = Boolean.TRUE.equals(transactionTemplate.execute(status -> {
            try {
                // Xóa giọng nói, chỉ định người dùng và tác nhân hiện đang đăng nhập
                int row = baseMapper.delete(new LambdaQueryWrapper<AgentVoicePrintEntity>()
                        .eq(AgentVoicePrintEntity::getId, voicePrintId)
                        .eq(AgentVoicePrintEntity::getCreator, userId));
                if (row != 1) {
                    status.setRollbackOnly(); // Đánh dấu giao dịch để khôi phục
                    return false;
                }

                return true;
            } catch (Exception e) {
                status.setRollbackOnly(); // Đánh dấu giao dịch để khôi phục
                log.error("删除声纹存在错误原因：{}", e.getMessage());
                throw new RenException(ErrorCode.VOICEPRINT_DELETE_ERROR);
            }
        }));
        // Chỉ khi xóa thành công dữ liệu giọng nói trong cơ sở dữ liệu thì dữ liệu của dịch vụ giọng nói mới được xóa.
        if(b){
            taskExecutor.execute(()-> {
                try {
                    cancelVoicePrint(voicePrintId);
                }catch (RuntimeException e) {
                    log.error("删除声纹存在运行时错误原因：{}，id：{}", e.getMessage(),voicePrintId);
                }
            });
        }
        return b;
    }

    @Override
    public List<AgentVoicePrintVO> list(Long userId, String agentId) {
        // Tìm dữ liệu theo người dùng và tác nhân hiện đang đăng nhập được chỉ định
        List<AgentVoicePrintEntity> list = baseMapper.selectList(new LambdaQueryWrapper<AgentVoicePrintEntity>()
                .eq(AgentVoicePrintEntity::getAgentId, agentId)
                .eq(AgentVoicePrintEntity::getCreator, userId));
        return list.stream().map(entity -> {
            // Di chuyển và chuyển đổi sang loại AgentVoicePrintVO
            return ConvertUtils.sourceToTarget(entity, AgentVoicePrintVO.class);
        }).toList();

    }

    @Override
    public boolean update(Long userId, AgentVoicePrintUpdateDTO dto) {
        AgentVoicePrintEntity agentVoicePrintEntity = baseMapper
                .selectOne(new LambdaQueryWrapper<AgentVoicePrintEntity>()
                        .eq(AgentVoicePrintEntity::getId, dto.getId())
                        .eq(AgentVoicePrintEntity::getCreator, userId));
        if (agentVoicePrintEntity == null) {
            return false;
        }
        // Nhận ID âm thanh
        String audioId = dto.getAudioId();
        // Nhận id đại lý
        String agentId = agentVoicePrintEntity.getAgentId();
        ByteArrayResource resource;
        // audioId không bằng trống và audioId khác với id âm thanh đã lưu trước đó, bạn cần lấy lại dữ liệu âm thanh để tạo giọng nói.
        if (!StringUtils.isEmpty(audioId) && !audioId.equals(agentVoicePrintEntity.getAudioId())) {
            resource = getVoicePrintAudioWAV(agentId, audioId);

            // Kiểm tra xem giọng nói này đã được đăng ký chưa
            IdentifyVoicePrintResponse response = identifyVoicePrint(agentId, resource);
            // Nếu điểm trả về cao hơn RECOGNITION, điều đó có nghĩa là giọng nói đã tồn tại
            if (response != null && response.getScore() > RECOGNITION) {
                // Nếu ID được trả về không phải là ID giọng nói cần sửa đổi, điều đó có nghĩa là ID giọng nói được đăng ký đã tồn tại và không phải là dấu giọng nói ban đầu và không được phép sửa đổi.
                if (!response.getSpeakerId().equals(dto.getId())) {
                    // Truy vấn thông tin người dùng tương ứng dựa trên ID giọng nói được nhận dạng
                    AgentVoicePrintEntity existingVoicePrint = baseMapper.selectById(response.getSpeakerId());
                    String existingUserName = existingVoicePrint != null ? existingVoicePrint.getSourceName() : "未知用户";
                    throw new RenException(ErrorCode.VOICEPRINT_UPDATE_NOT_ALLOWED, existingUserName);
                }
            }
        } else {
            resource = null;
        }
        // Mở giao dịch
        return Boolean.TRUE.equals(transactionTemplate.execute(status -> {
            try {
                AgentVoicePrintEntity entity = ConvertUtils.sourceToTarget(dto, AgentVoicePrintEntity.class);
                int row = baseMapper.updateById(entity);
                if (row != 1) {
                    status.setRollbackOnly(); // Đánh dấu giao dịch để khôi phục
                    return false;
                }
                if (resource != null) {
                    String id = entity.getId();
                    // Trước tiên, hãy đăng xuất vectơ dấu giọng nói trên ID dấu giọng nói trước đó.
                    cancelVoicePrint(id);
                    // Gửi yêu cầu đăng ký giọng nói
                    registerVoicePrint(id, resource);
                }
                return true;
            } catch (RenException e) {
                status.setRollbackOnly(); // Đánh dấu giao dịch để khôi phục
                throw e;
            } catch (Exception e) {
                status.setRollbackOnly(); // Đánh dấu giao dịch để khôi phục
                log.error("修改声纹错误原因：{}", e.getMessage());
                throw new RenException(ErrorCode.VOICEPRINT_UPDATE_ADMIN_ERROR);
            }
        }));
    }

    /**
     * Lấy đối tượng URI giao diện thô
     *
     * @return đối tượng URI
     */
    private URI getVoicePrintURI() {
        // Lấy địa chỉ giao diện voiceprint
        String voicePrint = sysParamsService.getValue(Constant.SERVER_VOICE_PRINT, true);
        try {
            return new URI(voicePrint);
        } catch (URISyntaxException e) {
            log.error("路径格式不正确路径：{}，\n错误信息:{}", voicePrint, e.getMessage());
                throw new RenException(ErrorCode.VOICEPRINT_API_URI_ERROR);
        }
    }

    /**
     * Nhận đường dẫn cơ sở của địa chỉ giọng nói
     * 
     * @param uri địa chỉ giọng nói uri
     * @return đường dẫn cơ sở
     */
    private String getBaseUrl(URI uri) {
        String protocol = uri.getScheme();
        String host = uri.getHost();
        int port = uri.getPort();
        if (port == -1) {
            return "%s://%s".formatted(protocol, host);
        } else {
            return "%s://%s:%s".formatted(protocol, host, port);
        }
    }

    /**
     * Nhận ủy quyền
     *
     * @param uri địa chỉ giọng nói uri
     * @return Giá trị ủy quyền
     */
    private String getAuthorization(URI uri) {
        // Nhận thông số
        String query = uri.getQuery();
        // Nhận khóa mã hóa aes
        String str = "key=";
        return "Bearer " + query.substring(query.indexOf(str) + str.length());
    }

    /**
     * Nhận dữ liệu tài nguyên âm thanh giọng nói
     *
     * @param audioId audioId
     * @return Dữ liệu tài nguyên âm thanh Voiceprint
     */
    private ByteArrayResource getVoicePrintAudioWAV(String agentId, String audioId) {
        // Xác định xem âm thanh này có thuộc về tác nhân hiện tại hay không
        boolean b = agentChatHistoryService.isAudioOwnedByAgent(audioId, agentId);
        if (!b) {
            throw new RenException(ErrorCode.VOICEPRINT_AUDIO_NOT_BELONG_AGENT);
        }
        // Nhận dữ liệu âm thanh
        byte[] audio = agentChatAudioService.getAudio(audioId);
        // Nếu dữ liệu âm thanh trống, lỗi sẽ được báo cáo trực tiếp và quá trình sẽ không tiếp tục.
        if (audio == null || audio.length == 0) {
            throw new RenException(ErrorCode.VOICEPRINT_AUDIO_EMPTY);
        }
        // Gói một mảng byte vào một tài nguyên, trả về
        return new ByteArrayResource(audio) {
            @Override
            public String getFilename() {
                return "VoicePrint.WAV"; // Đặt tên tập tin
            }
        };
    }

    /**
     * Gửi yêu cầu http giọng nói đăng ký
     * 
     * @param id id giọng nói
     * @param resource Tài nguyên âm thanh giọng nói
     */
    private void registerVoicePrint(String id, ByteArrayResource resource) {
        // Xử lý địa chỉ giao diện giọng nói và lấy tiền tố
        URI uri = getVoicePrintURI();
        String baseUrl = getBaseUrl(uri);
        String requestUrl = baseUrl + "/voiceprint/register";
        // Tạo nội dung yêu cầu
        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        body.add("speaker_id", id);
        body.add("file", resource);

        // Tạo tiêu đề yêu cầu
        HttpHeaders headers = new HttpHeaders();
        headers.set("Authorization", getAuthorization(uri));
        headers.setContentType(MediaType.MULTIPART_FORM_DATA);
        // Tạo nội dung yêu cầu
        HttpEntity<MultiValueMap<String, Object>> requestEntity = new HttpEntity<>(body, headers);
        // Gửi yêu cầu POST
        ResponseEntity<String> response = restTemplate.postForEntity(requestUrl, requestEntity, String.class);

        if (response.getStatusCode() != HttpStatus.OK) {
            log.error("声纹注册失败,请求路径：{}", requestUrl);
            throw new RenException(ErrorCode.VOICEPRINT_REGISTER_REQUEST_ERROR);
        }
        // Kiểm tra nội dung phản hồi
        String responseBody = response.getBody();
        if (responseBody == null || !responseBody.contains("true")) {
            log.error("声纹注册失败,请求处理失败内容：{}", responseBody == null ? "空内容" : responseBody);
            throw new RenException(ErrorCode.VOICEPRINT_REGISTER_PROCESS_ERROR);
        }
    }

    /**
     * Gửi yêu cầu hủy giọng nói của bạn
     * 
     * @param voicePrintId id giọng nói
     */
    private void cancelVoicePrint(String voicePrintId) {
        URI uri = getVoicePrintURI();
        String baseUrl = getBaseUrl(uri);
        String requestUrl = baseUrl + "/voiceprint/" + voicePrintId;
        // Tạo tiêu đề yêu cầu
        HttpHeaders headers = new HttpHeaders();
        headers.set("Authorization", getAuthorization(uri));
        // Tạo nội dung yêu cầu
        HttpEntity<MultiValueMap<String, Object>> requestEntity = new HttpEntity<>(headers);

        // Gửi yêu cầu POST
        ResponseEntity<String> response = restTemplate.exchange(requestUrl, HttpMethod.DELETE, requestEntity,
                String.class);
        if (response.getStatusCode() != HttpStatus.OK) {
            log.error("声纹注销失败,请求路径：{}", requestUrl);
            throw new RenException(ErrorCode.VOICEPRINT_UNREGISTER_REQUEST_ERROR);
        }
        // Kiểm tra nội dung phản hồi
        String responseBody = response.getBody();
        if (responseBody == null || !responseBody.contains("true")) {
            log.error("声纹注销失败,请求处理失败内容：{}", responseBody == null ? "空内容" : responseBody);
            throw new RenException(ErrorCode.VOICEPRINT_UNREGISTER_PROCESS_ERROR);
        }
    }

    /**
     * Gửi yêu cầu http để nhận dạng giọng nói
     * 
     * @param agentId id đại lý
     * @param resource Tài nguyên âm thanh giọng nói
     * @return trả về dữ liệu nhận dạng
     */
    private IdentifyVoicePrintResponse identifyVoicePrint(String agentId, ByteArrayResource resource) {

        // Nhận tất cả các giọng nói đã đăng ký của đại lý
        List<AgentVoicePrintEntity> agentVoicePrintList = baseMapper
                .selectList(new LambdaQueryWrapper<AgentVoicePrintEntity>()
                        .select(AgentVoicePrintEntity::getId)
                        .eq(AgentVoicePrintEntity::getAgentId, agentId));

        // Số lượng dấu giọng nói là 0, biểu thị rằng chưa có dấu giọng nói nào được đăng ký và không yêu cầu nhận dạng.
        if (agentVoicePrintList.isEmpty()) {
            return null;
        }
        // Xử lý địa chỉ giao diện giọng nói và lấy tiền tố
        URI uri = getVoicePrintURI();
        String baseUrl = getBaseUrl(uri);
        String requestUrl = baseUrl + "/voiceprint/identify";
        // Tạo nội dung yêu cầu
        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();

        // Tạo tham số loa_id
        String speakerIds = agentVoicePrintList.stream()
                .map(AgentVoicePrintEntity::getId)
                .collect(Collectors.joining(","));
        body.add("speaker_ids", speakerIds);
        body.add("file", resource);

        // Tạo tiêu đề yêu cầu
        HttpHeaders headers = new HttpHeaders();
        headers.set("Authorization", getAuthorization(uri));
        headers.setContentType(MediaType.MULTIPART_FORM_DATA);
        // Tạo nội dung yêu cầu
        HttpEntity<MultiValueMap<String, Object>> requestEntity = new HttpEntity<>(body, headers);
        // Gửi yêu cầu POST
        ResponseEntity<String> response = restTemplate.postForEntity(requestUrl, requestEntity, String.class);

        if (response.getStatusCode() != HttpStatus.OK) {
            log.error("声纹识别请求失败,请求路径：{}", requestUrl);
            throw new RenException(ErrorCode.VOICEPRINT_IDENTIFY_REQUEST_ERROR);
        }
        // Kiểm tra nội dung phản hồi
        String responseBody = response.getBody();
        if (responseBody != null) {
            return JsonUtils.parseObject(responseBody, IdentifyVoicePrintResponse.class);
        }
        return null;
    }
}
