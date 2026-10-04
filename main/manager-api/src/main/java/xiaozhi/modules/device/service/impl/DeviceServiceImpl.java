package xiaozhi.modules.device.service.impl;

import java.nio.charset.StandardCharsets;
import java.security.InvalidKeyException;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Base64;
import java.util.Collections;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.TimeZone;
import java.util.UUID;
import java.util.stream.Collectors;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

import org.apache.commons.lang3.StringUtils;
import org.springframework.aop.framework.AopContext;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.UpdateWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;

import cn.hutool.core.collection.CollUtil;
import cn.hutool.core.map.MapUtil;
import cn.hutool.core.util.RandomUtil;
import cn.hutool.core.util.StrUtil;
import cn.hutool.json.JSONArray;
import cn.hutool.json.JSONObject;
import cn.hutool.json.JSONUtil;
import jakarta.servlet.http.HttpServletRequest;
import lombok.AllArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import xiaozhi.common.constant.Constant;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.page.PageData;
import xiaozhi.common.redis.RedisKeys;
import xiaozhi.common.redis.RedisUtils;
import xiaozhi.common.service.impl.BaseServiceImpl;
import xiaozhi.common.user.UserDetail;
import xiaozhi.common.utils.ConvertUtils;
import xiaozhi.common.utils.DateUtils;
import xiaozhi.common.utils.JsonUtils;
import xiaozhi.modules.device.dao.DeviceDao;
import xiaozhi.modules.device.dto.DeviceManualAddDTO;
import xiaozhi.modules.device.dto.DevicePageUserDTO;
import xiaozhi.modules.device.dto.DeviceReportReqDTO;
import xiaozhi.modules.device.dto.DeviceReportRespDTO;
import xiaozhi.modules.device.entity.DeviceEntity;
import xiaozhi.modules.device.entity.OtaEntity;
import xiaozhi.modules.device.service.DeviceAddressBookService;
import xiaozhi.modules.device.service.DeviceService;
import xiaozhi.modules.device.service.OtaService;
import xiaozhi.modules.device.vo.UserShowDeviceListVO;
import xiaozhi.modules.security.user.SecurityUser;
import xiaozhi.modules.sys.service.SysParamsService;
import xiaozhi.modules.sys.service.SysUserUtilService;

@Slf4j
@Service
@AllArgsConstructor
public class DeviceServiceImpl extends BaseServiceImpl<DeviceDao, DeviceEntity> implements DeviceService {

    private final DeviceDao deviceDao;
    private final SysUserUtilService sysUserUtilService;
    private final SysParamsService sysParamsService;
    private final RedisUtils redisUtils;
    private final OtaService otaService;
    private final DeviceAddressBookService deviceAddressBookService;

    @Async
    public void updateDeviceConnectionInfo(String agentId, String deviceId, String appVersion) {
        try {
            DeviceEntity device = new DeviceEntity();
            device.setId(deviceId);
            device.setLastConnectedAt(new Date());
            if (StringUtils.isNotBlank(appVersion)) {
                device.setAppVersion(appVersion);
            }
            deviceDao.updateById(device);
            if (StringUtils.isNotBlank(agentId)) {
                redisUtils.set(RedisKeys.getAgentDeviceLastConnectedAtById(agentId), new Date());
            }
        } catch (Exception e) {
            log.error("异步更新设备连接信息失败", e);
        }
    }

    @Override
    public Boolean deviceActivation(String agentId, String activationCode) {
        if (StringUtils.isBlank(activationCode)) {
            throw new RenException(ErrorCode.ACTIVATION_CODE_EMPTY);
        }
        String deviceKey = RedisKeys.getOtaActivationCode(activationCode);
        String cacheDeviceId = (String) redisUtils.get(deviceKey);
        if (StringUtils.isBlank(cacheDeviceId)) {
            throw new RenException(ErrorCode.ACTIVATION_CODE_ERROR);
        }
        String deviceId = cacheDeviceId;
        String safeDeviceId = deviceId.replace(":", "_").toLowerCase();
        String cacheDeviceKey = RedisKeys.getOtaDeviceActivationInfo(safeDeviceId);
        Map<String, Object> cacheMap = JsonUtils.toStringObjectMap(redisUtils.get(cacheDeviceKey));
        if (MapUtil.isEmpty(cacheMap)) {
            throw new RenException(ErrorCode.ACTIVATION_CODE_ERROR);
        }
        String cachedCode = (String) cacheMap.get("activation_code");
        if (!activationCode.equals(cachedCode)) {
            throw new RenException(ErrorCode.ACTIVATION_CODE_ERROR);
        }
        // Kiểm tra xem thiết bị đã được kích hoạt chưa
        if (selectById(deviceId) != null) {
            throw new RenException(ErrorCode.DEVICE_ALREADY_ACTIVATED);
        }

        String macAddress = (String) cacheMap.get("mac_address");
        String board = (String) cacheMap.get("board");
        String appVersion = (String) cacheMap.get("app_version");
        UserDetail user = SecurityUser.getUser();
        if (user.getId() == null) {
            throw new RenException(ErrorCode.USER_NOT_LOGIN);
        }

        Date currentTime = new Date();
        DeviceEntity deviceEntity = new DeviceEntity();
        deviceEntity.setId(deviceId);
        deviceEntity.setBoard(board);
        deviceEntity.setAgentId(agentId);
        deviceEntity.setAppVersion(appVersion);
        deviceEntity.setMacAddress(macAddress);
        deviceEntity.setUserId(user.getId());
        deviceEntity.setCreator(user.getId());
        deviceEntity.setAutoUpdate(1);
        deviceEntity.setCreateDate(currentTime);
        deviceEntity.setUpdater(user.getId());
        deviceEntity.setUpdateDate(currentTime);
        deviceEntity.setLastConnectedAt(currentTime);
        deviceDao.insert(deviceEntity);

        // Xóa bộ đệm redis và xóa bộ đệm số thiết bị thông minh
        redisUtils.delete(List.of(cacheDeviceKey, deviceKey, RedisKeys.getAgentDeviceCountById(agentId)));
        return true;
    }

    /**
     * Nhận dữ liệu trực tuyến của thiết bị
     */
    @Override
    public String getDeviceOnlineData(String agentId) {
        // Nhận địa chỉ cổng MQTT từ các tham số hệ thống
        String mqttGatewayUrl = sysParamsService.getValue("server.mqtt_manager_api", true);
        if (StringUtils.isBlank(mqttGatewayUrl) || "null".equals(mqttGatewayUrl)) {
            return "";
        }
        // Xây dựng URL hoàn chỉnh
        String url = StrUtil.format("http://{}/api/devices/status", mqttGatewayUrl);

        // Lấy danh sách thiết bị của người dùng hiện tại
        UserDetail user = SecurityUser.getUser();
        List<DeviceEntity> devices = getUserDevices(user.getId(), agentId);

        // Xây dựng mảng deviceIds
        Set<String> deviceIds = devices.stream().map(o -> {
            String macAddress = Optional.ofNullable(o.getMacAddress()).orElse("unknown").replace(":", "_");
            String groupId = Optional.ofNullable(o.getBoard()).orElse("GID_default").replace(":", "_");
            return StrUtil.format("{}@@@{}@@@{}", groupId, macAddress, macAddress);
        }).collect(Collectors.toSet());

        // Xây dựng các tham số đầu vào yêu cầu
        Map<String, Set<String>> params = MapUtil
                .builder(new HashMap<String, Set<String>>())
                .put("clientIds", deviceIds).build();

        if (CollUtil.isNotEmpty(deviceIds)) {
            return postToMqttGateway(url, params);
        }
        // Trả lời phản hồi
        return "";
    }

    @Override
    public DeviceReportRespDTO checkDeviceActive(String macAddress, String clientId, DeviceReportReqDTO deviceReport) {
        DeviceReportRespDTO response = new DeviceReportRespDTO();
        response.setServer_time(buildServerTime());

        DeviceEntity deviceById = getDeviceByMacAddress(macAddress);

        // Nếu thiết bị không bị ràng buộc, thông tin firmware hiện đang tải lên sẽ được trả về (không cập nhật) để tương thích với các phiên bản firmware cũ hơn.
        if (deviceById == null) {
            DeviceReportRespDTO.Firmware firmware = new DeviceReportRespDTO.Firmware();
            firmware.setVersion(deviceReport.getApplication().getVersion());
            firmware.setUrl(Constant.INVALID_FIRMWARE_URL);
            response.setFirmware(firmware);
        } else {
            // Thông tin nâng cấp chương trình cơ sở sẽ chỉ được trả về khi thiết bị bị ràng buộc và nâng cấp tự động được bật rõ ràng.
            if (Integer.valueOf(1).equals(deviceById.getAutoUpdate())) {
                String type = deviceReport.getBoard() == null ? null : deviceReport.getBoard().getType();
                DeviceReportRespDTO.Firmware firmware = buildFirmwareInfo(type,
                        deviceReport.getApplication() == null ? null : deviceReport.getApplication().getVersion());
                response.setFirmware(firmware);
            }
        }

        // Thêm cấu hình WebSocket
        DeviceReportRespDTO.Websocket websocket = new DeviceReportRespDTO.Websocket();
        // Lấy URL WebSocket từ tham số hệ thống, sử dụng giá trị mặc định nếu không được định cấu hình
        String wsUrl = sysParamsService.getValue(Constant.SERVER_WEBSOCKET, true);

        // Kiểm tra xem xác thực có được bật hay không và tạo mã thông báo
        String authEnabled = sysParamsService.getValue(Constant.SERVER_AUTH_ENABLED, true);
        if ("true".equalsIgnoreCase(authEnabled)) {
            try {
                // Tạo mã thông báo
                String token = generateWebSocketToken(clientId, macAddress);
                websocket.setToken(token);
            } catch (Exception e) {
                log.error("生成WebSocket token失败: {}", e.getMessage());
                websocket.setToken("");
            }
        } else {
            websocket.setToken("");
        }

        if (StringUtils.isBlank(wsUrl) || wsUrl.equals("null")) {
            log.error("WebSocket地址未配置，请登录智控台，在参数管理找到【server.websocket】配置");
            wsUrl = "ws://xiaozhi.server.com:8000/xiaozhi/v1/";
            websocket.setUrl(wsUrl);
        } else {
            String[] wsUrls = wsUrl.split("\\;");
            if (wsUrls.length > 0) {
                // Chọn ngẫu nhiên một URL WebSocket
                websocket.setUrl(wsUrls[RandomUtil.randomInt(0, wsUrls.length)]);
            } else {
                log.error("WebSocket地址未配置，请登录智控台，在参数管理找到【server.websocket】配置");
                websocket.setUrl("ws://xiaozhi.server.com:8000/xiaozhi/v1/");
            }
        }

        response.setWebsocket(websocket);

        // Thêm cấu hình MQTT UDP
        // Lấy địa chỉ MQTT Gateway từ tham số hệ thống, chỉ sử dụng khi cấu hình hợp lệ
        String mqttUdpConfig = sysParamsService.getValue(Constant.SERVER_MQTT_GATEWAY, true);
        if (mqttUdpConfig != null && !mqttUdpConfig.equals("null") && !mqttUdpConfig.isEmpty()) {
            try {
                String groupId = deviceById != null && deviceById.getBoard() != null ? deviceById.getBoard()
                        : "GID_default";
                DeviceReportRespDTO.MQTT mqtt = buildMqttConfig(macAddress, groupId);
                if (mqtt != null) {
                    mqtt.setEndpoint(mqttUdpConfig);
                    response.setMqtt(mqtt);
                }
            } catch (Exception e) {
                log.error("生成MQTT配置失败: {}", e.getMessage());
            }
        }

        if (deviceById != null) {
            // Nếu thiết bị tồn tại, cập nhật không đồng bộ thông tin phiên bản và thời gian kết nối cuối cùng
            String appVersion = deviceReport.getApplication() != null ? deviceReport.getApplication().getVersion()
                    : null;
            // Gọi các phương thức không đồng bộ thông qua Spring proxy
            ((DeviceServiceImpl) AopContext.currentProxy()).updateDeviceConnectionInfo(deviceById.getAgentId(),
                    deviceById.getId(), appVersion);
        } else {
            // Nếu thiết bị không tồn tại, hãy tạo mã kích hoạt
            DeviceReportRespDTO.Activation code = buildActivation(macAddress, deviceReport);
            response.setActivation(code);
        }

        return response;
    }

    @Override
    public List<DeviceEntity> getUserDevices(Long userId, String agentId) {
        QueryWrapper<DeviceEntity> wrapper = new QueryWrapper<>();
        wrapper.eq("user_id", userId);
        wrapper.eq("agent_id", agentId);
        return baseDao.selectList(wrapper);
    }

    @Override
    public List<UserShowDeviceListVO> getUserDeviceList(Long userId, String agentId) {
        List<DeviceEntity> devices = getUserDevices(userId, agentId);
        return devices.stream().map(this::toUserShowDeviceListVO).toList();
    }

    private UserShowDeviceListVO toUserShowDeviceListVO(DeviceEntity device) {
        UserShowDeviceListVO vo = ConvertUtils.sourceToTarget(device, UserShowDeviceListVO.class);
        vo.setDeviceType(device.getBoard());
        vo.setBoard(device.getBoard());
        vo.setAutoUpdate(device.getAutoUpdate());
        vo.setCreateDateTimestamp(toTimestamp(device.getCreateDate()));
        vo.setLastConnectedAtTimestamp(toTimestamp(device.getLastConnectedAt()));
        return vo;
    }

    private Long toTimestamp(Date date) {
        return date == null ? null : date.getTime();
    }

    @Override
    public void unbindDevice(Long userId, String deviceId) {
        // Đầu tiên truy vấn thông tin thiết bị và lấy AgentId và macAddress
        DeviceEntity device = baseDao.selectById(deviceId);
        if (device == null) {
            return;
        }
        String macAddress = device.getMacAddress();
        if (StringUtils.isNotBlank(device.getAgentId())) {
            // Xóa bộ nhớ đệm đếm thiết bị của đại lý
            redisUtils.delete(RedisKeys.getAgentDeviceCountById(device.getAgentId()));
        }

        UpdateWrapper<DeviceEntity> wrapper = new UpdateWrapper<>();
        wrapper.eq("user_id", userId);
        wrapper.eq("id", deviceId);
        baseDao.delete(wrapper);

        // Xóa bản ghi quyền sổ địa chỉ liên quan đến thiết bị
        deviceAddressBookService.deleteByMacAddresses(Collections.singletonList(macAddress));
    }

    @Override
    public void deleteByUserId(Long userId) {
        UpdateWrapper<DeviceEntity> wrapper = new UpdateWrapper<>();
        wrapper.eq("user_id", userId);
        baseDao.delete(wrapper);
    }

    @Override
    public Long selectCountByUserId(Long userId) {
        UpdateWrapper<DeviceEntity> wrapper = new UpdateWrapper<>();
        wrapper.eq("user_id", userId);
        return baseDao.selectCount(wrapper);
    }

    @Override
    public void deleteByAgentId(String agentId) {
        // Trước tiên, hãy truy vấn tất cả các thiết bị thuộc đại lý và lấy địa chỉ mac để xóa các bản ghi sổ địa chỉ.
        QueryWrapper<DeviceEntity> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("agent_id", agentId);
        List<DeviceEntity> devices = baseDao.selectList(queryWrapper);

        // Xóa thiết bị
        UpdateWrapper<DeviceEntity> wrapper = new UpdateWrapper<>();
        wrapper.eq("agent_id", agentId);
        baseDao.delete(wrapper);

        // Xóa tất cả các bản ghi quyền sổ địa chỉ liên quan đến các thiết bị này theo đợt
        if (!devices.isEmpty()) {
            List<String> macAddresses = devices.stream()
                    .map(DeviceEntity::getMacAddress)
                    .collect(Collectors.toList());
            deviceAddressBookService.deleteByMacAddresses(macAddresses);
        }
    }

    @Override
    public PageData<UserShowDeviceListVO> page(DevicePageUserDTO dto) {
        Map<String, Object> params = new HashMap<String, Object>();
        params.put(Constant.PAGE, dto.getPage());
        params.put(Constant.LIMIT, dto.getLimit());
        IPage<DeviceEntity> page = baseDao.selectPage(
                getPage(params, "mac_address", true),
                // Xác định điều kiện truy vấn
                new QueryWrapper<DeviceEntity>()
                        // Tìm kiếm từ khóa thiết bị cần thiết
                        .like(StringUtils.isNotBlank(dto.getKeywords()), "alias", dto.getKeywords()));
        // Lặp lại dữ liệu được lấy từ trang và trả về các trường bắt buộc
        List<UserShowDeviceListVO> list = page.getRecords().stream().map(device -> {
            UserShowDeviceListVO vo = toUserShowDeviceListVO(device);
            // Thay đổi thời gian sửa đổi lần cuối thành thời gian mô tả ngắn gọn
            vo.setRecentChatTime(DateUtils.getShortTime(device.getUpdateDate()));
            sysUserUtilService.assignUsername(device.getUserId(),
                    vo::setBindUserName);
            return vo;
        }).toList();
        // Đếm trang
        return new PageData<>(list, page.getTotal());
    }

    @Override
    public DeviceEntity getDeviceByMacAddress(String macAddress) {
        if (StringUtils.isBlank(macAddress)) {
            return null;
        }
        QueryWrapper<DeviceEntity> wrapper = new QueryWrapper<>();
        wrapper.eq("mac_address", macAddress);
        return baseDao.selectOne(wrapper);
    }

    private DeviceReportRespDTO.ServerTime buildServerTime() {
        DeviceReportRespDTO.ServerTime serverTime = new DeviceReportRespDTO.ServerTime();
        TimeZone tz = TimeZone.getDefault();
        serverTime.setTimestamp(Instant.now().toEpochMilli());
        serverTime.setTimeZone(tz.getID());
        serverTime.setTimezone_offset(tz.getOffset(System.currentTimeMillis()) / (60 * 1000));
        return serverTime;
    }

    @Override
    public String geCodeByDeviceId(String deviceId) {
        String dataKey = getDeviceCacheKey(deviceId);

        Map<String, Object> cacheMap = JsonUtils.toStringObjectMap(redisUtils.get(dataKey));
        if (cacheMap != null && cacheMap.containsKey("activation_code")) {
            String cachedCode = (String) cacheMap.get("activation_code");
            return cachedCode;
        }
        return null;
    }

    @Override
    public Date getLatestLastConnectionTime(String agentId) {
        // Truy vấn xem có thời gian bộ đệm hay không và quay lại nếu có
        Date cachedDate = (Date) redisUtils.get(RedisKeys.getAgentDeviceLastConnectedAtById(agentId));
        if (cachedDate != null) {
            return cachedDate;
        }
        Date maxDate = deviceDao.getAllLastConnectedAtByAgentId(agentId);
        if (maxDate != null) {
            redisUtils.set(RedisKeys.getAgentDeviceLastConnectedAtById(agentId), maxDate);
        }
        return maxDate;
    }

    private String getDeviceCacheKey(String deviceId) {
        String safeDeviceId = deviceId.replace(":", "_").toLowerCase();
        return RedisKeys.getOtaDeviceActivationInfo(safeDeviceId);
    }

    public DeviceReportRespDTO.Activation buildActivation(String deviceId, DeviceReportReqDTO deviceReport) {
        DeviceReportRespDTO.Activation code = new DeviceReportRespDTO.Activation();

        String cachedCode = geCodeByDeviceId(deviceId);

        if (StringUtils.isNotBlank(cachedCode)) {
            code.setCode(cachedCode);
            String frontedUrl = sysParamsService.getValue(Constant.SERVER_FRONTED_URL, true);
            code.setMessage(frontedUrl + "\n" + cachedCode);
            code.setChallenge(deviceId);
        } else {
            String newCode = RandomUtil.randomNumbers(6);
            code.setCode(newCode);
            String frontedUrl = sysParamsService.getValue(Constant.SERVER_FRONTED_URL, true);
            code.setMessage(frontedUrl + "\n" + newCode);
            code.setChallenge(deviceId);

            Map<String, Object> dataMap = new HashMap<>();
            dataMap.put("id", deviceId);
            dataMap.put("mac_address", deviceId);

            dataMap.put("board", (deviceReport.getBoard() != null && deviceReport.getBoard().getType() != null)
                    ? deviceReport.getBoard().getType()
                    : (deviceReport.getChipModelName() != null ? deviceReport.getChipModelName() : "unknown"));
            dataMap.put("app_version", (deviceReport.getApplication() != null)
                    ? deviceReport.getApplication().getVersion()
                    : null);

            dataMap.put("deviceId", deviceId);
            dataMap.put("activation_code", newCode);

            // Viết khóa dữ liệu chính
            String dataKey = getDeviceCacheKey(deviceId);
            redisUtils.set(dataKey, dataMap);

            // Viết key mã kích hoạt chống kiểm tra
            String codeKey = RedisKeys.getOtaActivationCode(newCode);
            redisUtils.set(codeKey, deviceId);
        }
        return code;
    }

    private DeviceReportRespDTO.Firmware buildFirmwareInfo(String type, String currentVersion) {
        if (StringUtils.isBlank(type)) {
            return null;
        }
        if (StringUtils.isBlank(currentVersion)) {
            currentVersion = "0.0.0";
        }

        OtaEntity ota = otaService.getLatestOta(type);
        DeviceReportRespDTO.Firmware firmware = new DeviceReportRespDTO.Firmware();
        String downloadUrl = null;

        if (ota != null) {
            // Nếu thiết bị không có thông tin phiên bản hoặc phiên bản OTA mới hơn phiên bản thiết bị thì địa chỉ tải sẽ được trả về.
            if (compareVersions(ota.getVersion(), currentVersion) > 0) {
                String otaUrl = sysParamsService.getValue(Constant.SERVER_OTA, true);
                if (StringUtils.isBlank(otaUrl) || otaUrl.equals("null")) {
                    log.error("OTA地址未配置，请登录智控台，在参数管理找到【server.ota】配置");
                    // Cố gắng nhận được từ yêu cầu
                    HttpServletRequest request = ((ServletRequestAttributes) RequestContextHolder
                            .getRequestAttributes())
                            .getRequest();
                    otaUrl = request.getRequestURL().toString();
                }
                // Thay thế /ota/ trong URL bằng /otaMag/download/
                String uuid = UUID.randomUUID().toString();
                redisUtils.set(RedisKeys.getOtaIdKey(uuid), ota.getId());
                downloadUrl = otaUrl.replace("/ota/", "/otaMag/download/") + uuid;
            }
        }

        firmware.setVersion(ota == null ? currentVersion : ota.getVersion());
        firmware.setUrl(downloadUrl == null ? Constant.INVALID_FIRMWARE_URL : downloadUrl);
        return firmware;
    }

    /**
     * So sánh hai số phiên bản
     * 
     * @param version1 bản1 phiên bản 1
     * @param version2 bản2 phiên bản 2
     * @return Nếu version1 > version2 trả về 1, version1 < version2 trả về -1, nếu bằng nhau trả về 0
     */
    private static int compareVersions(String version1, String version2) {
        if (version1 == null || version2 == null) {
            return 0;
        }

        String[] v1Parts = version1.split("\\.");
        String[] v2Parts = version2.split("\\.");

        int length = Math.max(v1Parts.length, v2Parts.length);
        for (int i = 0; i < length; i++) {
            int v1 = i < v1Parts.length ? Integer.parseInt(v1Parts[i]) : 0;
            int v2 = i < v2Parts.length ? Integer.parseInt(v2Parts[i]) : 0;

            if (v1 > v2) {
                return 1;
            } else if (v1 < v2) {
                return -1;
            }
        }
        return 0;
    }

    @Override
    public void manualAddDevice(Long userId, DeviceManualAddDTO dto) {
        // Kiểm tra xem mac đã tồn tại chưa
        QueryWrapper<DeviceEntity> wrapper = new QueryWrapper<>();
        wrapper.eq("mac_address", dto.getMacAddress());
        DeviceEntity exist = baseDao.selectOne(wrapper);
        if (exist != null) {
            throw new RenException(ErrorCode.MAC_ADDRESS_ALREADY_EXISTS);
        }
        Date now = new Date();
        DeviceEntity entity = new DeviceEntity();
        entity.setId(dto.getMacAddress());
        entity.setUserId(userId);
        entity.setAgentId(dto.getAgentId());
        entity.setBoard(dto.getBoard());
        entity.setAppVersion(dto.getAppVersion());
        entity.setMacAddress(dto.getMacAddress());
        entity.setCreateDate(now);
        entity.setUpdateDate(now);
        entity.setLastConnectedAt(now);
        entity.setCreator(userId);
        entity.setUpdater(userId);
        entity.setAutoUpdate(1);
        baseDao.insert(entity);

        // Đã thêm: Xóa bộ nhớ đệm đếm thiết bị của đại lý
        redisUtils.delete(RedisKeys.getAgentDeviceCountById(dto.getAgentId()));
    }

    @Override
    public List<DeviceEntity> searchDevicesByMacAddress(String macAddress, Long userId) {
        QueryWrapper<DeviceEntity> wrapper = new QueryWrapper<>();
        wrapper.like("mac_address", macAddress);
        wrapper.eq("user_id", userId);
        return deviceDao.selectList(wrapper);
    }

    /**
     * Tạo chữ ký mật mã MQTT
     * 
     * @param content Nội dung chữ ký (clientId + '|' + tên người dùng)
     * @param secretKey khóa
     * @return Chữ ký HMAC-SHA256 được mã hóa Base64
     */
    private String generatePasswordSignature(String content, String secretKey) throws Exception {
        Mac hmac = Mac.getInstance("HmacSHA256");
        SecretKeySpec keySpec = new SecretKeySpec(secretKey.getBytes(StandardCharsets.UTF_8), "HmacSHA256");
        hmac.init(keySpec);
        byte[] signature = hmac.doFinal(content.getBytes(StandardCharsets.UTF_8));
        return Base64.getEncoder().encodeToString(signature);
    }

    /**
     * Tạo mã thông báo xác thực WebSocket theo logic triển khai của AuthManager phía Python: token = signature.timestamp
     * 
     * @param clientId ID máy khách
     * @param username người dùng tên người dùng (thường là deviceId/macAddress)
     * @return chuỗi mã thông báo xác thực
     */
    public String generateWebSocketToken(String clientId, String username)
            throws NoSuchAlgorithmException, InvalidKeyException {
        // Lấy key từ tham số hệ thống
        String secretKey = sysParamsService.getValue(Constant.SERVER_SECRET, false);
        if (StringUtils.isBlank(secretKey)) {
            throw new IllegalStateException("WebSocket认证密钥未配置(server.secret)");
        }

        // Lấy dấu thời gian hiện tại (giây)
        long timestamp = System.currentTimeMillis() / 1000;

        // Xây dựng nội dung chữ ký: clientId|tên người dùng|dấu thời gian
        String content = String.format("%s|%s|%d", clientId, username, timestamp);

        // Tạo chữ ký HMAC-SHA256
        Mac hmac = Mac.getInstance("HmacSHA256");
        SecretKeySpec keySpec = new SecretKeySpec(secretKey.getBytes(StandardCharsets.UTF_8), "HmacSHA256");
        hmac.init(keySpec);
        byte[] signature = hmac.doFinal(content.getBytes(StandardCharsets.UTF_8));

        // Chữ ký được mã hóa an toàn URL Base64 (xóa phần đệm =)
        String signatureBase64 = Base64.getUrlEncoder().withoutPadding().encodeToString(signature);

        // Định dạng trả về: signature.timestamp
        return String.format("%s.%d", signatureBase64, timestamp);
    }

    /**
     * Xây dựng thông tin cấu hình MQTT
     * 
     * @param macAddress chỉ địa chỉ MAC
     * @param groupId nhóm ID nhóm
     * @return Đối tượng cấu hình MQTT
     */
    private DeviceReportRespDTO.MQTT buildMqttConfig(String macAddress, String groupId)
            throws Exception {
        // Lấy khóa ký từ biến môi trường hoặc tham số hệ thống
        String signatureKey = sysParamsService.getValue("server.mqtt_signature_key", true);
        if (StringUtils.isBlank(signatureKey)) {
            log.warn("缺少MQTT_SIGNATURE_KEY，跳过MQTT配置生成");
            return null;
        }

        // Tạo ID máy khách theo định dạng: groupId@@@macAddress@@@uuid
        String groupIdSafeStr = groupId.replace(":", "_");
        String deviceIdSafeStr = macAddress.replace(":", "_");
        String mqttClientId = String.format("%s@@@%s@@@%s", groupIdSafeStr, deviceIdSafeStr, deviceIdSafeStr);

        // Xây dựng dữ liệu người dùng (bao gồm IP và thông tin khác)
        Map<String, String> userData = new HashMap<>();
        // Thử lấy IP của máy khách
        try {
            ServletRequestAttributes attributes = (ServletRequestAttributes) RequestContextHolder
                    .getRequestAttributes();
            if (attributes != null) {
                HttpServletRequest request = attributes.getRequest();
                String clientIp = request.getRemoteAddr();
                userData.put("ip", clientIp);
            }
        } catch (Exception e) {
            userData.put("ip", "unknown");
        }

        // Mã hóa dữ liệu người dùng thành Base64 JSON
        String userDataJson = new com.fasterxml.jackson.databind.ObjectMapper().writeValueAsString(userData);
        String username = Base64.getEncoder().encodeToString(userDataJson.getBytes(StandardCharsets.UTF_8));

        // Tạo chữ ký mật mã
        String password = generatePasswordSignature(mqttClientId + "|" + username, signatureKey);

        // Xây dựng cấu hình MQTT
        DeviceReportRespDTO.MQTT mqtt = new DeviceReportRespDTO.MQTT();
        mqtt.setClient_id(mqttClientId);
        mqtt.setUsername(username);
        mqtt.setPassword(password);
        mqtt.setPublish_topic("device-server");
        mqtt.setSubscribe_topic("devices/p2p/" + deviceIdSafeStr);

        return mqtt;
    }

    private String postToMqttGateway(String url, Object requestBody) {
        String signatureKey = sysParamsService.getValue(Constant.SERVER_MQTT_SECRET, false);
        return MqttGatewayAuthorization.postJson(
                url,
                JSONUtil.toJsonStr(requestBody),
                signatureKey,
                Instant.now());
    }

    @Override
    public Object getDeviceTools(String deviceId) {
        // Nhận địa chỉ cổng MQTT từ các tham số hệ thống
        String mqttGatewayUrl = sysParamsService.getValue("server.mqtt_manager_api", true);
        if (StringUtils.isBlank(mqttGatewayUrl) || "null".equals(mqttGatewayUrl)) {
            return null;
        }

        // Nhận thông tin thiết bị
        DeviceEntity device = baseDao.selectById(deviceId);
        if (device == null) {
            return null;
        }

        // Kiểm tra xem thiết bị có thuộc về người dùng hiện tại không
        UserDetail user = SecurityUser.getUser();
        if (!device.getUserId().equals(user.getId())) {
            return null;
        }

        // Xây dựng clientId
        String macAddress = Optional.ofNullable(device.getMacAddress()).orElse("unknown").replace(":", "_");
        String groupId = Optional.ofNullable(device.getBoard()).orElse("GID_default").replace(":", "_");
        String clientId = StrUtil.format("{}@@@{}@@@{}", groupId, macAddress, macAddress);

        // Xây dựng URL hoàn chỉnh
        String url = StrUtil.format("http://{}/api/commands/{}", mqttGatewayUrl, clientId);

        // Lưu trữ danh sách tất cả các công cụ
        List<Object> allTools = new ArrayList<>();
        String cursor = null;

        // Vòng lặp để lấy dữ liệu được phân trang
        while (true) {
            // Xây dựng thông số
            Map<String, Object> paramsMap = MapUtil.builder(new HashMap<String, Object>())
                    .put("withUserTools", true)
                    .build();
            // Nếu có con trỏ, hãy thêm nó vào tham số yêu cầu
            if (StringUtils.isNotBlank(cursor)) {
                paramsMap.put("cursor", cursor);
            }

            // Xây dựng nội dung yêu cầu
            Map<String, Object> payload = MapUtil
                    .builder(new HashMap<String, Object>())
                    .put("jsonrpc", "2.0")
                    .put("id", 2)
                    .put("method", "tools/list")
                    .put("params", paramsMap)
                    .build();

            Map<String, Object> requestBody = MapUtil
                    .builder(new HashMap<String, Object>())
                    .put("type", "mcp")
                    .put("payload", payload)
                    .build();

            String resultMessage = postToMqttGateway(url, requestBody);

            // Phân tích phản hồi
            if (StringUtils.isBlank(resultMessage)) {
                break;
            }

            JSONObject jsonObject = JSONUtil.parseObj(resultMessage);
            if (!jsonObject.getBool("success", false)) {
                break;
            }

            JSONObject data = jsonObject.getJSONObject("data");
            if (data == null) {
                break;
            }

            // Lấy danh sách công cụ của trang hiện tại
            JSONArray tools = data.getJSONArray("tools");
            if (tools != null && !tools.isEmpty()) {
                allTools.addAll(tools);
            }

            // Lấy con trỏ của trang tiếp theo
            String nextCursor = data.getStr("nextCursor");
            if (StringUtils.isBlank(nextCursor)) {
                // Không có trang tiếp theo
                break;
            }
            cursor = nextCursor;
        }

        // Xây dựng kết quả trả về
        if (allTools.isEmpty()) {
            return null;
        }

        Map<String, Object> resultData = new HashMap<>();
        resultData.put("tools", allTools);
        return resultData;
    }

    @Override
    public Object callDeviceTool(String deviceId, String toolName, Map<String, Object> arguments) {
        // Nhận địa chỉ cổng MQTT từ các tham số hệ thống
        String mqttGatewayUrl = sysParamsService.getValue("server.mqtt_manager_api", true);
        if (StringUtils.isBlank(mqttGatewayUrl) || "null".equals(mqttGatewayUrl)) {
            return null;
        }

        // Nhận thông tin thiết bị
        DeviceEntity device = baseDao.selectById(deviceId);
        if (device == null) {
            return null;
        }

        // Kiểm tra xem thiết bị có thuộc về người dùng hiện tại không
        UserDetail user = SecurityUser.getUser();
        if (!device.getUserId().equals(user.getId())) {
            return null;
        }

        // Xây dựng clientId
        String macAddress = Optional.ofNullable(device.getMacAddress()).orElse("unknown").replace(":", "_");
        String groupId = Optional.ofNullable(device.getBoard()).orElse("GID_default").replace(":", "_");
        String clientId = StrUtil.format("{}@@@{}@@@{}", groupId, macAddress, macAddress);

        // Xây dựng URL hoàn chỉnh
        String url = StrUtil.format("http://{}/api/commands/{}", mqttGatewayUrl, clientId);

        // Xây dựng nội dung yêu cầu
        Map<String, Object> params = MapUtil
                .builder(new HashMap<String, Object>())
                .put("name", toolName)
                .put("arguments", arguments)
                .build();

        Map<String, Object> payload = MapUtil
                .builder(new HashMap<String, Object>())
                .put("jsonrpc", "2.0")
                .put("id", 2)
                .put("method", "tools/call")
                .put("params", params)
                .build();

        Map<String, Object> requestBody = MapUtil
                .builder(new HashMap<String, Object>())
                .put("type", "mcp")
                .put("payload", payload)
                .build();

        String resultMessage = postToMqttGateway(url, requestBody);

        // Phân tích phản hồi
        if (StringUtils.isNotBlank(resultMessage)) {
            cn.hutool.json.JSONObject jsonObject = JSONUtil.parseObj(resultMessage);
            if (jsonObject.getBool("success", false)) {
                cn.hutool.json.JSONObject data = jsonObject.getJSONObject("data");
                if (data != null) {
                    cn.hutool.json.JSONArray content = data.getJSONArray("content");
                    if (content != null && content.size() > 0) {
                        cn.hutool.json.JSONObject firstContent = content.getJSONObject(0);
                        if (firstContent != null && "text".equals(firstContent.getStr("type"))) {
                            String text = firstContent.getStr("text");
                            if (StringUtils.isNotBlank(text)) {
                                String trimmedText = text.trim();
                                if (trimmedText.startsWith("{") || trimmedText.startsWith("[")) {
                                    try {
                                        return JSONUtil.parseObj(trimmedText);
                                    } catch (Exception e) {
                                        return trimmedText;
                                    }
                                } else if ("true".equals(trimmedText)) {
                                    return true;
                                } else if ("false".equals(trimmedText)) {
                                    return false;
                                } else {
                                    return trimmedText;
                                }
                            }
                        }
                    }
                }
            }
        }
        return null;
    }
}
