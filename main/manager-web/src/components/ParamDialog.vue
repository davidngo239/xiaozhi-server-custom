<template>
  <CustomDialog
    :title="title"
    :visible.sync="visible"
    width="600px"
    class="param-dialog-wrapper"
    @confirm="submit"
    @close="cancel"
    :confirmLoading="saving"
  >
    <div class="dialog-container">
      <el-form :model="form" :rules="rules" ref="form" label-width="auto" label-position="left" class="param-form">
        <el-form-item :label="$t('paramDialog.paramCode')" prop="paramCode" class="form-item">
          <el-input v-model="form.paramCode" :placeholder="$t('paramDialog.paramCodePlaceholder')"
            class="custom-input"></el-input>
        </el-form-item>

        <el-form-item :label="$t('paramDialog.valueType')" prop="valueType" class="form-item">
          <el-select
            v-model="form.valueType"
            :placeholder="$t('paramDialog.valueTypePlaceholder')"
            class="custom-select"
          >
            <el-option
              v-for="item in valueTypeOptions"
              :key="item.value"
              :label="$t(`paramDialog.${item.value}Type`)"
              :value="item.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item :label="$t('paramDialog.paramValue')" prop="paramValue" class="form-item">
          <el-input
            v-if="form.valueType !== 'json' && form.valueType !== 'array'"
            v-model="form.paramValue"
            :placeholder="$t('paramDialog.paramValuePlaceholder')"
            class="custom-input"
          ></el-input>
          <el-input
            v-else
            type="textarea"
            v-model="form.paramValue"
            :placeholder="$t('paramDialog.paramValuePlaceholder')"
            :rows="6"
            class="custom-textarea"
          ></el-input>
        </el-form-item>

        <el-form-item :label="$t('paramDialog.remark')" prop="remark" class="form-item remark-item">
          <el-input type="textarea" v-model="form.remark" :placeholder="$t('paramDialog.remarkPlaceholder')" :rows="3"
            class="custom-textarea"></el-input>
        </el-form-item>
      </el-form>
    </div>
  </CustomDialog>
</template>

<script>
import CustomDialog from './CustomDialog.vue';
export default {
  props: {
    title: {
      type: String,
      default: 'Thêm tham số'
    },
    visible: {
      type: Boolean,
      default: false
    },
    form: {
      type: Object,
      default: () => ({
        id: null,
        paramCode: '',
        paramValue: '',
        valueType: 'string',
        remark: ''
      })
    }
  },
  components: {
    CustomDialog
  },
  data() {
    return {
      dialogKey: Date.now(),
      saving: false,
      valueTypeOptions: [
        { value: 'string' },
        { value: 'number' },
        { value: 'boolean' },
        { value: 'array' },
        { value: 'json' }
      ],
      rules: {
        paramCode: [
          { required: true, message: this.$t('paramDialog.requiredParamCode'), trigger: "blur" }
        ],
        paramValue: [
          { required: true, message: this.$t('paramDialog.requiredParamValue'), trigger: "blur" }
        ],
        valueType: [
          { required: true, message: this.$t('paramDialog.requiredValueType'), trigger: "change" }
        ]
      }
    };
  },
  methods: {
    submit() {
      this.$refs.form.validate((valid) => {
        if (valid) {
          const submitData = { ...this.form };

          // Nếu là kiểu mảng, hãy kiểm tra định dạng và chuyển đổi
          if (submitData.valueType === 'array' && submitData.paramValue) {
            const lines = submitData.paramValue.split('\n').filter(line => line.trim());

            // Kiểm tra xem mọi dòng ngoại trừ dòng cuối cùng có kết thúc bằng dấu chấm phẩy không
            for (let i = 0; i < lines.length - 1; i++) {
              if (!lines[i].trim().endsWith(';')) {
                this.$message.error('Định dạng mảng không hợp lệ, cần kết thúc bằng dấu chấm phẩy (;)');
                return;
              }
            }

            const items = lines
              .map(item => item.trim().replace(/;$/, ''))
              .filter(item => item);
            submitData.paramValue = items.join(';');
          }
          // Nếu nó thuộc loại json, hãy nén nó ở định dạng JSON trước khi gửi.
          else if (submitData.valueType === 'json' && submitData.paramValue) {
            try {
              const parsed = JSON.parse(submitData.paramValue);
              submitData.paramValue = JSON.stringify(parsed);
            } catch (e) {
              // Nếu phân tích cú pháp không thành công, hãy giữ nguyên giá trị ban đầu
            }
          }

          this.saving = true; // Bắt đầu tải
          this.$emit('submit', submitData);
        }
      });
    },
    cancel() {
      this.saving = false; // Đặt lại trạng thái khi hủy
      this.dialogKey = Date.now();
      this.$emit('cancel');
    },

    // Cung cấp cho thành phần cha mẹ để gọi để thiết lập lại trạng thái lưu
    resetSaving() {
      this.saving = false;
    }
  },
  watch: {
    visible(newVal) {
      if (newVal) {
        if (this.form.paramValue) {
          // Nếu là loại json, định dạng và hiển thị
          if (this.form.valueType === 'json') {
            try {
              const parsed = JSON.parse(this.form.paramValue);
              this.form.paramValue = JSON.stringify(parsed, null, 2);
            } catch (e) {
              // Nếu phân tích cú pháp không thành công, hãy giữ nguyên giá trị ban đầu
            }
          }
          // Nếu thuộc loại mảng, hãy chuyển đổi một chuỗi được phân cách bằng dấu chấm phẩy thành một mục trên mỗi dòng
          else if (this.form.valueType === 'array') {
            const items = this.form.paramValue.split(';').filter(item => item.trim());
            this.form.paramValue = items.join(';\n');
          }
        }
      } else {
        // Khi hộp thoại đóng lại, đặt lại trạng thái lưu
        this.saving = false;
      }
    }
  }
};
</script>

<style>
.custom-param-dialog {
  border-radius: 16px !important;
  overflow: hidden;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15) !important;
  border: none !important;

  .el-dialog__header {
    display: none;
  }

  .el-dialog__body {
    padding: 0 !important;
    border-radius: 16px;
  }
}
</style>

<style scoped lang="scss">
.param-dialog-wrapper {
  .param-form {
    .form-item {
      margin-bottom: 20px;
      :deep(.el-form-item__label) {
        color: #475569;
        font-weight: 500;
        padding-right: 12px;
        text-align: right;
        font-size: 14px;
        letter-spacing: 0.2px;
      }
    }

    .custom-input {
      :deep(.el-input__inner) {
        background-color: #ffffff;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        height: 42px;
        padding: 0 14px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        font-size: 14px;
        color: #334155;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);

        &:focus {
          border-color: #3b82f6;
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
          background-color: #ffffff;
        }

        &::placeholder {
          color: #94a3b8;
          font-weight: 400;
        }
      }
    }

    .custom-select {
      width: 100%;

      :deep(.el-input__inner) {
        background-color: #ffffff;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        height: 42px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        font-size: 14px;
        color: #334155;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);

        &:focus {
          border-color: #3b82f6;
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
          background-color: #ffffff;
        }

        &::placeholder {
          color: #94a3b8;
          font-weight: 400;
        }
      }
    }

    .custom-textarea {
      :deep(.el-textarea__inner) {
        background-color: #ffffff;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        padding: 12px 14px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        font-size: 14px;
        color: #334155;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
        line-height: 1.5;

        &:focus {
          border-color: #3b82f6;
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
          background-color: #ffffff;
        }

        &::placeholder {
          color: #94a3b8;
          font-weight: 400;
        }
      }
    }

    .remark-item :deep(.el-form-item__label) {
      margin-top: -4px;
    }
  }
}
</style>
