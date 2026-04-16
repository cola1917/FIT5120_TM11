import { router } from 'expo-router';
import {
    BookOpen,
    Compass,
    Flag,
    ScanLine,
    X,
} from 'lucide-react-native';
import React, { useEffect, useRef } from 'react';
import {
    Animated,
    Modal,
    Pressable,
    StyleSheet,
    Text,
    TouchableOpacity,
    View,
} from 'react-native';

type SideMenuProps = {
  visible: boolean;
  onClose: () => void;
};

export default function SideMenu({ visible, onClose }: SideMenuProps) {
  // Animated values for the dark overlay and sliding panel.
  const slideAnim = useRef(new Animated.Value(-320)).current;
  const overlayAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    // Animate the side menu in and out based on visibility.
    if (visible) {
      Animated.parallel([
        Animated.timing(slideAnim, {
          toValue: 0,
          duration: 240,
          useNativeDriver: true,
        }),
        Animated.timing(overlayAnim, {
          toValue: 1,
          duration: 240,
          useNativeDriver: true,
        }),
      ]).start();
    } else {
      Animated.parallel([
        Animated.timing(slideAnim, {
          toValue: -320,
          duration: 200,
          useNativeDriver: true,
        }),
        Animated.timing(overlayAnim, {
          toValue: 0,
          duration: 200,
          useNativeDriver: true,
        }),
      ]).start();
    }
  }, [overlayAnim, slideAnim, visible]);

  const handleNavigate = (path: '/goal' | '/scan' | '/stories') => {
    // Close the menu first, then navigate after a short delay.
    onClose();
    setTimeout(() => {
      router.push(path);
    }, 180);
  };

  return (
    <Modal visible={visible} transparent animationType="none">
      <View style={styles.root}>
        {/* Dark overlay behind the side menu */}
        <Animated.View style={[styles.overlay, { opacity: overlayAnim }]}>
          <Pressable style={styles.overlayPressable} onPress={onClose} />
        </Animated.View>

        {/* Sliding side menu panel */}
        <Animated.View
          style={[
            styles.panel,
            {
              transform: [{ translateX: slideAnim }],
            },
          ]}
        >
          <View style={styles.headerRow}>
            <Text style={styles.headerTitle}>NutriHeroes</Text>

            <TouchableOpacity style={styles.closeButton} onPress={onClose}>
              <X size={20} color="#B45309" />
            </TouchableOpacity>
          </View>

          <Text style={styles.headerSubtitle}>Choose where to go</Text>

          {/* Primary navigation items */}
          <View style={styles.menuList}>
            <MenuItem
              icon={<Flag size={20} color="#B45309" />}
              label="Goal"
              onPress={() => handleNavigate('/goal')}
            />

            <MenuItem
              icon={<ScanLine size={20} color="#B45309" />}
              label="Scan"
              onPress={() => handleNavigate('/scan')}
            />

            <MenuItem
              icon={<BookOpen size={20} color="#B45309" />}
              label="Stories"
              onPress={() => handleNavigate('/stories')}
            />
          </View>
        </Animated.View>
      </View>
    </Modal>
  );
}

type MenuItemProps = {
  icon: React.ReactNode;
  label: string;
  onPress: () => void;
};

function MenuItem({ icon, label, onPress }: MenuItemProps) {
  return (
    <TouchableOpacity style={styles.menuItem} onPress={onPress} activeOpacity={0.9}>
      <View style={styles.menuIconWrap}>{icon}</View>
      <Text style={styles.menuLabel}>{label}</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    flexDirection: 'row',
  },
  overlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.38)',
  },
  overlayPressable: {
    flex: 1,
  },
  panel: {
    width: 300,
    height: '100%',
    backgroundColor: '#1C1A20',
    paddingTop: 58,
    paddingHorizontal: 16,
    shadowColor: '#000',
    shadowOpacity: 0.28,
    shadowRadius: 12,
    shadowOffset: { width: 4, height: 0 },
    elevation: 12,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  headerTitle: {
    fontSize: 28,
    fontWeight: '900',
    color: '#F7E7D0',
  },
  closeButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#FFF3E3',
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerSubtitle: {
    fontSize: 14,
    color: '#C8B9AB',
    marginBottom: 18,
    fontWeight: '600',
  },
  menuList: {
    gap: 12,
  },
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#26242B',
    borderRadius: 18,
    paddingVertical: 16,
    paddingHorizontal: 14,
  },
  menuIconWrap: {
    width: 36,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 8,
  },
  menuLabel: {
    fontSize: 17,
    fontWeight: '800',
    color: '#F6EFE7',
  },
});
