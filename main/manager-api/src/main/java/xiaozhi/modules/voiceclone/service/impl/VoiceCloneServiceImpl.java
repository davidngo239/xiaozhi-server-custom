package xiaozhi.modules.voiceclone.service.impl;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.*;
import java.util.stream.Collectors;

import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;

import cn.hutool.core.collection.CollUtil;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import xiaozhi.common.constant.Constant;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.page.PageData;
import xiaozhi.common.service.impl.BaseServiceImpl;
import xiaozhi.common.utils.ConvertUtils;
import xiaozhi.common.utils.DateUtils;
import xiaozhi.modules.model.entity.ModelConfigEntity;
import xiaozhi.modules.model.service.ModelConfigService;
import xiaozhi.modules.sys.dao.SysUserDao;
import xiaozhi.modules.sys.entity.SysUserEntity;
import xiaozhi.modules.sys.service.SysUserService;
import xiaozhi.modules.voiceclone.dao.VoiceCloneDao;
import xiaozhi.modules.voiceclone.dto.VoiceCloneDTO;
import xiaozhi.modules.voiceclone.dto.VoiceCloneResponseDTO;
import xiaozhi.modules.voiceclone.entity.VoiceCloneEntity;
import xiaozhi.modules.voiceclone.service.VoiceCloneService;

@Slf4j
@Service
@RequiredArgsConstructor
public class VoiceCloneServiceImpl extends BaseServiceImpl<VoiceCloneDao, VoiceCloneEntity>
        implements VoiceCloneService {

    private final ModelConfigService modelConfigService;
    private final SysUserService sysUserService;
    private final SysUserDao sysUserDao;
    private final ObjectMapper objectMapper;

    @Override
    public PageData<VoiceCloneEntity> page(Map<String, Object> params) {
        IPage<VoiceCloneEntity> page = baseDao.selectPage(
                getPage(params, "create_date", true),
                getWrapper(params));

        return new PageData<>(page.getRecords(), page.getTotal());
    }

    private QueryWrapper<VoiceCloneEntity> getWrapper(Map<String, Object> params) {
        String name = (String) params.get("name");
        String userId = (String) params.get("userId");

        QueryWrapper<VoiceCloneEntity> wrapper = new QueryWrapper<>();
        wrapper.eq(StringUtils.isNotBlank(userId), "user_id", userId);
        if (StringUtils.isNotBlank(name)) {
            wrapper.and(w -> w.like("name", name)
                    .or().eq("voice_id", name));
        }
        return wrapper;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void save(VoiceCloneDTO dto) {
        ModelConfigEntity modelConfig = modelConfigService.getModelByIdFromCache(dto.getModelId());
        if (modelConfig == null || modelConfig.getConfigJson() == null) {
            throw new RenException(ErrorCode.VOICE_CLONE_MODEL_CONFIG_NOT_FOUND);
        }
        Map<String, Object> config = modelConfig.getConfigJson();
        String type = (String) config.get("type");
        if (StringUtils.isBlank(type)) {
            throw new RenException(ErrorCode.VOICE_CLONE_MODEL_TYPE_NOT_FOUND);
        }

        // Kiểm tra xem Voice ID đã được sử dụng chưa
        for (String voiceId : dto.getVoiceIds()) {
            if (StringUtils.isBlank(voiceId)) {
                continue;
            }
            if (Constant.VOICE_CLONE_HUOSHAN_DOUBLE_STREAM.equals(type)) {
                if (voiceId.indexOf("S_") == -1) {
                    throw new RenException(ErrorCode.VOICE_CLONE_HUOSHAN_VOICE_ID_ERROR);
                }
            }

            QueryWrapper<VoiceCloneEntity> wrapper = new QueryWrapper<>();
            wrapper.eq("voice_id", voiceId);
            wrapper.eq("model_id", dto.getModelId());
            Long count = baseDao.selectCount(wrapper);
            if (count > 0) {
                throw new RenException(ErrorCode.VOICE_ID_ALREADY_EXISTS);
            }
        }

        // Lưu theo đợt
        List<VoiceCloneEntity> batchInsertList = new ArrayList<>();
        // Duyệt qua các ID âm sắc đã chọn và tạo bản ghi cho từng ID âm sắc
        int index = 0;
        String namePrefix = DateUtils.format(new Date(), "MMddHHmm");
        for (String voiceId : dto.getVoiceIds()) {
            index++;
            VoiceCloneEntity entity = new VoiceCloneEntity();
            entity.setModelId(dto.getModelId());
            entity.setVoiceId(voiceId);
            entity.setName(namePrefix + "_" + index);
            entity.setUserId(dto.getUserId());
            entity.setLanguages(dto.getLanguages());
            entity.setTrainStatus(0); // Đào tạo mặc định
            batchInsertList.add(entity);
        }
        if (CollUtil.isNotEmpty(batchInsertList)) {
            insertBatch(batchInsertList);
        }
    }

    @Override
    public void delete(String[] ids) {
        baseDao.deleteByIds(Arrays.asList(ids));
    }

    @Override
    public List<VoiceCloneEntity> getByUserId(Long userId) {
        QueryWrapper<VoiceCloneEntity> wrapper = new QueryWrapper<>();
        wrapper.eq("user_id", userId);
        wrapper.orderByDesc("created_at");
        return baseDao.selectList(wrapper);
    }

    @Override
    public PageData<VoiceCloneResponseDTO> pageWithNames(Map<String, Object> params) {
        // Truy vấn dữ liệu phân trang trước
        IPage<VoiceCloneEntity> page = baseDao.selectPage(
                getPage(params, "create_date", true),
                getWrapper(params));

        // Chuyển đổi danh sách thực thể thành danh sách DTO
        List<VoiceCloneResponseDTO> dtoList = convertToResponseDTOList(page.getRecords());

        return new PageData<>(dtoList, page.getTotal());
    }

    @Override
    public VoiceCloneResponseDTO getByIdWithNames(String id) {
        VoiceCloneEntity entity = baseDao.selectById(id);
        if (entity == null) {
            return null;
        }

        VoiceCloneResponseDTO dto = ConvertUtils.sourceToTarget(entity, VoiceCloneResponseDTO.class);

        // Đặt tên mẫu
        if (StringUtils.isNotBlank(entity.getModelId())) {
            dto.setModelName(modelConfigService.getModelNameById(entity.getModelId()));
        }

        // Đặt tên người dùng
        if (entity.getUserId() != null) {
            dto.setUserName(sysUserService.getByUserId(entity.getUserId()).getUsername());
        }
        
        // Đảm bảo trường trainStatus được đặt chính xác. Giao diện người dùng cần trường này để xác định xem đó có phải là âm thanh nhân bản hay không.
        dto.setTrainStatus(entity.getTrainStatus());

        return dto;
    }

    @Override
    public List<VoiceCloneResponseDTO> getByUserIdWithNames(Long userId) {
        List<VoiceCloneEntity> entityList = getByUserId(userId);
        return convertToResponseDTOList(entityList);
    }

    /**
     * Chuyển đổi danh sách VoiceCloneEntity thành danh sách VoiceCloneResponseDTO
     */
    private List<VoiceCloneResponseDTO> convertToResponseDTOList(List<VoiceCloneEntity> entityList) {
        if (entityList == null || entityList.isEmpty()) {
            return new ArrayList<>();
        }

        List<VoiceCloneResponseDTO> dtoList = new ArrayList<>(entityList.size());

        // Nhận bộ sưu tập ID tên người dùng
        Set<Long> userIdList = entityList.stream().map(VoiceCloneEntity::getUserId).collect(Collectors.toSet());
        List<SysUserEntity> userList = sysUserDao.selectList(new QueryWrapper<SysUserEntity>().in("id", userIdList));
        Map<Long, String> userMap = userList.stream().collect(Collectors.toMap(SysUserEntity::getId, SysUserEntity::getUsername));

        // Chuyển đổi từng thực thể thành DTO
        for (VoiceCloneEntity entity : entityList) {
            VoiceCloneResponseDTO dto = ConvertUtils.sourceToTarget(entity, VoiceCloneResponseDTO.class);

            // Đặt tên mẫu
            if (StringUtils.isNotBlank(entity.getModelId())) {
                dto.setModelName(modelConfigService.getModelNameById(entity.getModelId()));
            }

            // Đặt tên người dùng
            if (entity.getUserId() != null) {
                dto.setUserName(userMap.get(entity.getUserId()));
            }
            
            // Đảm bảo trường trainStatus được đặt chính xác. Giao diện người dùng cần trường này để xác định xem đó có phải là âm thanh nhân bản hay không.
            dto.setTrainStatus(entity.getTrainStatus());

            // Đặt xem có dữ liệu âm thanh hay không
            dto.setHasVoice(entity.getVoice() != null);

            dtoList.add(dto);
        }

        return dtoList;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void uploadVoice(String id, MultipartFile voiceFile) throws Exception {
        // Truy vấn bản ghi bản sao âm thanh
        VoiceCloneEntity entity = baseDao.selectById(id);
        if (entity == null) {
            throw new RenException(ErrorCode.VOICE_CLONE_RECORD_NOT_EXIST);
        }

        // Đọc tệp âm thanh và chuyển đổi nó thành một mảng byte
        byte[] voiceData = voiceFile.getBytes();

        // Cập nhật trường giọng nói
        entity.setVoice(voiceData);
        // Cập nhật trạng thái đào tạo thành đào tạo đang chờ xử lý
        entity.setTrainStatus(0);

        // Lưu vào cơ sở dữ liệu
        baseDao.updateById(entity);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void updateName(String id, String name) {
        // Truy vấn bản ghi bản sao âm thanh
        VoiceCloneEntity entity = baseDao.selectById(id);
        if (entity == null) {
            throw new RenException(ErrorCode.VOICE_CLONE_RECORD_NOT_EXIST);
        }

        // Cập nhật tên
        entity.setName(name);
        baseDao.updateById(entity);
    }

    @Override
    public byte[] getVoiceData(String id) {
        VoiceCloneEntity entity = baseDao.selectById(id);
        if (entity == null) {
            return null;
        }
        return entity.getVoice();
    }

    @Override
    // @Transactional(rollbackFor = Exception.class)
    public void cloneAudio(String cloneId) {
        VoiceCloneEntity entity = baseDao.selectById(cloneId);
        if (entity == null) {
            throw new RenException(ErrorCode.VOICE_CLONE_RECORD_NOT_EXIST);
        }
        if (entity.getVoice() == null || entity.getVoice().length == 0) {
            throw new RenException(ErrorCode.VOICE_CLONE_AUDIO_NOT_UPLOADED);
        }

        try {

            ModelConfigEntity modelConfig = modelConfigService.getModelByIdFromCache(entity.getModelId());
            if (modelConfig == null || modelConfig.getConfigJson() == null) {
                throw new RenException(ErrorCode.VOICE_CLONE_MODEL_CONFIG_NOT_FOUND);
            }
            Map<String, Object> config = modelConfig.getConfigJson();
            String type = (String) config.get("type");
            if (StringUtils.isBlank(type)) {
                throw new RenException(ErrorCode.VOICE_CLONE_MODEL_TYPE_NOT_FOUND);
            }
            if (Constant.VOICE_CLONE_HUOSHAN_DOUBLE_STREAM.equals(type)) {
                huoshanClone(config, entity);
            }
        } catch (RenException re) {
            entity.setTrainStatus(3);
            entity.setTrainError(re.getMsg());
            baseDao.updateById(entity);
            throw re;
        } catch (Exception e) {
            e.printStackTrace();
            entity.setTrainStatus(3);
            entity.setTrainError(e.getMessage());
            baseDao.updateById(entity);
            throw new RenException(ErrorCode.VOICE_CLONE_TRAINING_FAILED, e.getMessage());
        }
    }

    /**
     * Gọi công cụ Volcano để đào tạo tái tạo giọng nói
     * 
     * @param config Cấu hình mô hình
     * @param entity Thực thể ghi âm bản sao giọng nói
     * @throws entity
     */
    private void huoshanClone(Map<String, Object> config, VoiceCloneEntity entity) throws Exception {
        String appid = (String) config.get("appid");
        String accessToken = (String) config.get("access_token");

        if (StringUtils.isAnyBlank(appid, accessToken)) {
            throw new RenException(ErrorCode.VOICE_CLONE_HUOSHAN_CONFIG_MISSING);
        }

        String audioBase64 = Base64.getEncoder().encodeToString(entity.getVoice());
        Map<String, Object> reqBody = new HashMap<>();
        reqBody.put("appid", appid);
        List<Map<String, String>> audios = new ArrayList<>();
        Map<String, String> audioMap = new HashMap<>();
        audioMap.put("audio_bytes", audioBase64);
        audioMap.put("audio_format", "wav");
        audios.add(audioMap);
        reqBody.put("audios", audios);
        reqBody.put("source", 2);
        reqBody.put("language", 0);
        reqBody.put("model_type", 1);
        reqBody.put("speaker_id", entity.getVoiceId());

        String apiUrl = "https://openspeech.bytedance.com/api/v1/mega_tts/audio/upload";

        HttpClient client = HttpClient.newHttpClient();
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(apiUrl))
                .header("Content-Type", "application/json")
                .header("Authorization", "Bearer;" + accessToken)
                .header("Resource-Id", "seed-icl-1.0")
                .POST(HttpRequest.BodyPublishers.ofString(objectMapper.writeValueAsString(reqBody)))
                .build();
        HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());

        System.out.println(">>> HTTP status = " + response.statusCode());
        System.out.println(">>> response body = " + response.body());

        Map<String, Object> rsp = objectMapper.readValue(response.body(),
                new TypeReference<Map<String, Object>>() {
                });

        // Nhận đối tượng BaseResp
        Map<String, Object> baseResp = objectMapper.convertValue(rsp.get("BaseResp"),
                new TypeReference<Map<String, Object>>() {
                });
        if (baseResp != null) {
            Integer statusCode = objectMapper.convertValue(baseResp.get("StatusCode"), Integer.class);
            String statusMessage = objectMapper.convertValue(baseResp.getOrDefault("StatusMessage", ""),
                    String.class);

            // Nhận loa_id
            String speakerId = objectMapper.convertValue(rsp.get("speaker_id"), String.class);

            // StatusCode == 0 biểu thị thành công
            if (statusCode != null && statusCode == 0 && StringUtils.isNotBlank(speakerId)) {
                entity.setTrainStatus(2);
                entity.setVoiceId(speakerId);
                entity.setTrainError("");
                baseDao.updateById(entity);
            } else {
                // Sử dụng StatusMessage làm thông báo lỗi khi thất bại
                String errorMsg = StringUtils.isNotBlank(statusMessage) ? statusMessage : "训练失败";
                throw new RenException(errorMsg);
            }
        } else {
            String errorMsg = objectMapper.convertValue(rsp.get("message"),
                    new TypeReference<String>() {
                    });
            if (StringUtils.isNotBlank(errorMsg)) {
                throw new RenException(errorMsg);
            }
            throw new RenException(ErrorCode.VOICE_CLONE_RESPONSE_FORMAT_ERROR);
        }
    }
}
