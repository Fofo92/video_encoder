# frozen_string_literal: true

module VideoEncoder
  class FFmpegConfig
    def initialize(data)
      @data = data
    end

    def container
      @data.fetch('container', 'mkv')
    end

    def video_codec
      @data.fetch('video_codec', 'hevc_nvenc')
    end

    def preset
      @data.fetch('preset', 'p6')
    end

    def tune
      @data.fetch('tune', 'hq')
    end

    def rc
      @data.fetch('rc', 'vbr_hq')
    end

    def cq
      @data.fetch('cq', 22)
    end

    def audio_codec
      @data.fetch('audio_codec', 'aa3')
    end

    def deinterlace
      @data.fetch('deinterlace', true)
    end

    def spatial_aq
      @data.fetch('spatial_aq', true)
    end

    def aq_strength
      @data.fetch('aq_strength', 8)
    end

    def b_ref_mode
      @data.fetch('b_ref_mode', 'middle')
    end

    def max_width
      @data['max_width']
    end

    def max_height
      @data['max_height']
    end
  end
end
