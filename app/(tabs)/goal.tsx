/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import AppHeader from '@/components/app_header';
import {
  Baby,
  Dumbbell,
  Glasses,
  Lightbulb,
  ShieldPlus,
  Smile
} from 'lucide-react-native';
import React, { useEffect, useState } from 'react';
import {
  Dimensions,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import BeStrongDetail from '../../components/goal/BeStrongDetail';
import FeelGoodDetail from '../../components/goal/FeelGoodDetail';
import FightGermsDetail from '../../components/goal/FightGermsDetail';
import GrowUpDetail from '../../components/goal/GrowUpDetail';
import SeeClearDetail from '../../components/goal/SeeClearDetail';
import ThinkFastDetail from '../../components/goal/ThinkFastDetail';
import type { Alternative, Goal, SuperFood, TryLess } from '../../components/goal/types';
import { getUserProfile } from '../../services/userProfile';
import { getRecommendations, type RecommendationResponse } from '../../services/recommendations';

// Re-export types for backward compatibility with imports like `import { Goal } from '../types'`
export type { Alternative, Goal, SuperFood, TryLess };

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const CARD_WIDTH = (SCREEN_WIDTH - 120) / 2;

const GOALS: Goal[] = [
  {
    id: 'grow',
    title: 'POWER STRONGER',
    subtitle: 'Grow Like a Hero!',
    icon: Baby,
    gradient: ['#6366f1', '#8b5cf6'],
    tilt: 'left',
    bgIcon: 'height',
    description: 'Eat these magical foods to grow tall and mighty like a superhero giraffe! 🦒✨',
    mascotTip: 'Milk and yogurt have Calcium for super strong bones!',
    superFoods: [
      { name: 'Milk', description: 'Full of calcium power!', image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBAAN8pyCJaVEN3Z9OM2cCtC0v9rv0SRiwOBuedIG-CeNACdVUSdZLATA9ey-GITNpkCVM3usfXh7z-IPU9LiwseDOpn9ndOR1GXyEF8yK8KVVCXOGDgE97tot7_uyoX1UQwerS2bodrZdCBz_0YnqetE-XAtjg2-qRUi6Afnh3H2Tnf09CjKaL8cGx7JhBrul4-v1hXv9fSHaMbs2QPH2tKa0jvYbX_h18BqkzuZ6kPluI5HnhSclsHcaz6OEtUXUV9Kwwx7KIx0g6' },
      { name: 'Yogurt', description: 'Good Choice', image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuA59RTQO9WCupNWaxpUgsW0iy6EzGSIyvIUJT3UUt-YI_C-fiPl2p9uHk6pKwoCGWI22bH7RoW9hJYp8D-pwMo9vlXKzkDGa0mOXgnHxH9WXmB4URuu5fgQTiUoFq_sNKQvHTxM0D6zsiPWhYDXtzB5OXC3_tvga9dbQBHRzKb9iHsudXqaLfHxLPKxuZuRluaTYkE5w64g3p4Ti2-z8aAve8RkTZVQkrWkgLb1Mm0990ia2hPpTRAuX-bQ5wCFFelvXQO_T6mVFVeL' },
      { name: 'Cheese', description: 'Good Choice', image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBEF-fW0UWYUpxrfPiKRrfEcnKXXTlY0JW96uJrCSUZCiWU2Mpkf9qRO-Wpvg9kicasOx1sFsVDzEjgX645m9SPHfJFR4rsWyNMofBHoCJ2qz_Lobm6tbfxirReHfDPRXSRXpBdMLpEUbHiUIWeWG-7Tn7nCEnj5CssfgTt_gW4ZWVW6D60mEicDdsFiWbwHvo5QqPZQOhT2O8zOP-znMR92nLQ271xNOS8eTqzimYmXFSp2x6GbOa8LtYd7lSsYhOQ5VnOLAU06b8h' }
    ],
    tryLess: {
      name: 'Soda',
      image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBRZi73b1XLlPyAqjqGf0uaomtuIrI81M39yBXWvked1mYZv9p8Y3fnzmZSgze_-6GZA4Dkkdr1KrDkWvBJZ1hyOMlutuRtqYzLf2Tc4_oir7nOgyQLv5QnXibpGYyl_gsYlyBK7fKGwrhB5SaEO9lpgpvaUWmN1riacwPDU593xO5YnjOYY7hn-xCmdOeOXuhchsff8q8MG3JZ8s6bUv_oMZD5niIXxDLBjYNVIaZl-dthxAOUu0TKOstkJo6k4CTVOxvZP1S8RejL',
      alternative: {
        name: 'Water',
        image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuABIYSiqeJG-n4rBSzxjbjZiyjNDEPomJLU5A4Ulpgk_ptMZEL-4rRu63NXCA8loR9Ukc_qChJkOLfvcAVhTfQb5JxAgxaFi-hk6Dal5slbvJ2a2NiIhLpD7lMu6Q5AlaoJ12wBqwBBaEq2tsJeJsYcTUn8Mr5fciVpSISfsCextbYWyNsUzkkbiUbI3NSdYu29mwTAsvmV2qOu3PbmcGjc0uziXWZeWoGK13shDMJkagu6IK9tQcwFTIMfUA5SkLTuojUd_TzZ4Ium',
        tip: 'Wow! Swapping soda for water gives you hero-strength hydration! 💧'
      }
    }
  },
  {
    id: 'see',
    title: 'SUPER VISION',
    subtitle: 'Eagle Eyes!',
    icon: Glasses,
    gradient: ['#a855f7', '#f97316'],
    tilt: 'right',
    bgIcon: 'visibility',
    description: 'Fuel your eyes with these magical foods for amazing super-vision! 👀✨',
    mascotTip: 'Carrots have Vitamin A to help you see in the dark! 🥕✨',
    superFoods: [
      { name: 'Carrots', description: 'Mega dose of Beta-Carotene for night vision!', image: 'https://tse3.mm.bing.net/th/id/OIP.6AM2gH5CTSKuvKjK2qy4ZwHaFD?rs=1&pid=ImgDetMain&o=7&rm=3', rating: 2 },
      { name: 'Blueberries', description: 'Protect your retina with powerful antioxidants.', image: 'https://pic.nximg.cn/file/20230811/33760392_173922575125_2.jpg', rating: 2 },
      { name: 'Spinach', description: 'Lutein shields your eyes like magic sunglasses!', image: 'https://tse1.mm.bing.net/th/id/OIP.RjIHGF6ropplJEO9Ai2_0QHaGH?rs=1&pid=ImgDetMain&o=7&rm=3', rating: 2 }
    ],
    tryLess: {
      name: 'Sticky Candy',
      image: 'https://th.bing.com/th/id/OIP.pMg98I__KtLWLxHmPSSi0wHaHa?o=7rm=3&rs=1&pid=ImgDetMain&o=7&rm=3',
      alternative: {
        name: 'Blueberries',
        image: 'https://pic.nximg.cn/file/20230811/33760392_173922575125_2.jpg',
        tip: 'Sweet berries are way better for your super-vision than sticky candy! 🫐'
      }
    }
  },
  {
    id: 'think',
    title: 'SMART BOOST',
    subtitle: 'Genius Mode!',
    icon: Lightbulb,
    gradient: ['#401500', '#dc2626'],
    tilt: 'right',
    bgIcon: 'bolt',
    description: 'Power up your brilliant brain with these super-smart snacks! 🧠💡',
    mascotTip: 'Healthy fats in nuts and fish help your brain think super fast!',
    superFoods: [
      { name: 'Walnuts', description: 'Brain-shaped power nuts!', image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDFHG-LX8gcRuY6NcsLl30vobCgQNPOWA_tJMlRrXss85MsSgb91D9gS9VdWUPCv88IOCHo-WikCyhD5U2LCnJ2MNsX7LI7YJJeb2puaBPA7vSj97iGKVufNkAuVQWVmmeqOTth0Ii9Gm6gNZFRz5cZUnAJGpHxpzm590smBFfI7FKCKVru46vdWWLTMeEHpFYoVUD4n9aVyz3IX4Aad3t7f7bB-dzMMbLb0faWANBGsfxAKpcJ8tVdU4Zk7T4YyuKGpOGBKRsSNJFE', rating: 2 },
      { name: 'Fish', description: 'Freshly grilled salmon power!', image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuArer2tViX3FsVLtHxPiziLwqgUL8g9-hbzILfllY8BN5H3wz7xx5paKLzV3hXrU3GcvzrJM6-vMPbugFX0Csgw02RJxIePzhJ5r0h-2kJTCzjMH7pGBAvSQjh7N_h3bfrU2OQnjpYS5NcZAjfYNmsQWDA39P-5I4zS8cV6Ho3bxfI3BVvTTiRAc4bW0NO2NNRSCBtBjQKibnieNw4xLhZeDTphIwZSyorJGDizhJ8MvO0PjBMP0crWh0Sp1VFVKpyricSBc9xfG-vm', rating: 2 },
      { name: 'Eggs', description: 'Farm fresh brain fuel!', image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBTZwlFS468dUbE6FHT1MmwUEE68epBGwzbgj-cYm66SQab_MImjPiXBvL-dp_22gGYZhhdNxlL3jwXy__hHwa9Olgs_qrTOQSvIymjZTDLRH44fwVTlbPHk9-WQ1j7Qy_y5OFIx9QUj7iwCzzLGhE9Mo76Uyhc4j__8XE7i_0Z34yMzsobZJk_t_WOkT0vbvgCjMklg1F88oaXaXr-yUEiWYP9q7u2KkaGixAjDKte9dAXfOUbIAa6wS7Wac3ugZmC1_f67LZfOQt0', rating: 2 }
    ],
    tryLess: {
      name: 'Sugary Cereal',
      image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuA3l18mMu8egzIf93FCMqzDZslbpxUVfWCHDuGe3Yrs1oWU9dDpCr7GDrLqV8Q1Y_4jmt7AjbrZsUzZtzOiKKYhUBb8FkbpHwuIpUQ0NQTZrO6vPjGnQ6XM04ajFddoFSxQF3qAhbClf-YPN6egZJa3eDnAyBe4ob2E-m84h5Atjqu5yfdSiTbqawJUb9f9fpfekmeIX-YKoo3Gx84N_aOjg-do_YkZbm4ne0xcMXdHMKHru1ZtlpE-yL68dEizaJTRWoCk_89c7jeM',
      alternative: {
        name: 'Oatmeal & Eggs',
        image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBTZwlFS468dUbE6FHT1MmwUEE68epBGwzbgj-cYm66SQab_MImjPiXBvL-dp_22gGYZhhdNxlL3jwXy__hHwa9Olgs_qrTOQSvIymjZTDLRH44fwVTlbPHk9-WQ1j7Qy_y5OFIx9QUj7iwCzzLGhE9Mo76Uyhc4j__8XE7i_0Z34yMzsobZJk_t_WOkT0vbvgCjMklg1F88oaXaXr-yUEiWYP9q7u2KkaGixAjDKte9dAXfOUbIAa6wS7Wac3ugZmC1_f67LZfOQt0',
        tip: 'Sugary cereal makes your brain sleepy. Try oatmeal or eggs for super-speed thinking!'
      }
    }
  },
  {
    id: 'fight',
    title: 'GERM BUSTER',
    subtitle: 'Shield Power!',
    icon: ShieldPlus,
    gradient: ['#f97316', '#dc2626'],
    tilt: 'left',
    bgIcon: 'shield',
    description: 'Build your ultimate hero shield to zap away those sneaky germs! 🛡️⚡',
    mascotTip: 'Vitamin C helps your body\'s army fight off bad germs!',
    superFoods: [
      { name: 'Oranges', description: 'Fresh juicy orange slices!', image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDWL3m7aSDhAM7TeweNVJzXstmgJDQE5rv18jxz33migH-XdcMo-HB_693WAu2LX97cNZ26n-xHcEpV99oQ8qFtf5-Zsv33OezvcpLwDChemhrcW27BDqeF2yxY8Cwwl6Kqur9qTdpUVt_9kxx9J81E3DS55qj8EMWnxd6T_OTfMBSEJXZzoRax1MwE4hh9OAublBK3LvpzNJ18YtdYM0deS8BEkg_kw5eMZQx8_ehJd334ERZBwMgFnOGBUGYH9EZTM3La8XkF92es', rating: 3 },
      { name: 'Kiwi', description: 'Bright green Vitamin C power!', image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDC7h02EIWkYFj8N-Z7EOIqn5h2VNS3jDY7j26oUQKncHr-UOpXcedRcduJ1MyT9AesYDehd8jKPUg0wGod7M3_9OkCqXUF7d5ndERDWzbrhzckXElFGcKLDSachkPcAc2N_5EGPqccD-v_YTcHHNpDTDeK2mnuLmc9QtHYxDXzt9-PXzxO4dBY_srjnshUjL9OBKEx7b6_oYqYpnB6Nedk5LrXKegAruv5AMkV3mFuBZ-pxvJLeUk9KChpiGQS5fk75CtntBGfFTxT', rating: 2 },
      { name: 'Broccoli', description: 'Fresh green shield florets!', image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBruwTr90Rqkk3h16J__vOnbXXrG38WVcTabwnE480znUtmMM9kp0McquztBK3IrQUz9qnInFWLWYfjzEygdyzECsvdPjAhjWag2uCoDaeWpqvFMm14T1Dc6ebr1U7MEcZhHdJvmU75UcsDYsRUnMf2qIAkI6gPcHmnL5wmAKOEmfAGoJosyh_F52m_li7f6hfz8YJrWFRolnPsdAhep_oHZRsRrIgL7g0av5g9WOlpXKA0ielCQqOyONI1K-YH6D_ncAurjimnwAic', rating: 2 }
    ],
    tryLess: {
      name: 'Fried Food',
      image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDAs9Z8j-rmoTY3Yl0Jq9dWoz56txNIunU0XE-H2DAynXYY8v87ZTzlRfilggtTitXlmCZa6CXYjmhpn5q_new1Yf2dkFRbRdPxeGK-v-eFsIcTyptut0HZLZVadM8ofK92SHuSzlYZ0ledQqdofRmpN8ZELic4-OkfPstlqOBjrh26al2YtT45oKy6Ys_mHQguKDc5fl2lgjJlKAeGF6aXKXBnPwA9MFlRI2yLtbIyM4vnM16nkgAjJ4KROezb9Xhj68_HRrGICwjd',
      alternative: {
        name: 'Fresh Orange',
        image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCtZtbWAv3dylul1_YRGGeQRKMqOcNMfp3kTd8qDG63me9yz10Hv2_n3Ced9Y5K7we25aMHX-m2y0WzItFyK4Kyjd33Y3R6AaCyXx6emZZzwzBERZNQoegdSzfQOqMNQJe_xBHtsJ5M6IXFIxpJKm7A1Ef_Bb1SqLxt80yFMVEi0ny5BT3U9vs7nf0xb5SvFNuowvDSQXJ2Isb-hANT1qw2db1sLcIfJT86rdNAfRR4s4uYeCBr6-8qmOvGHJfu56Ce8FejQzOAqmDC',
        tip: 'Mega Vitamin C!'
      }
    }
  },
  {
    id: 'feel',
    title: 'HAPPY HERO',
    subtitle: 'Smile Shine!',
    icon: Smile,
    gradient: ['#facc15', '#f97316'],
    tilt: 'left',
    bgIcon: 'sentiment_very_satisfied',
    description: 'Munch on these happy foods for a joyful heart and mega smiles! 😊🌟',
    mascotTip: 'Whole grains and fruit give you steady energy for a great mood!',
    superFoods: [
      { name: 'Banana', description: 'Instant smile!', image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBrJkclsYpDmz3-b1gZiSIRbPkPZi79PP7NVytOwnp1wHtYjmCFItK2e5L9iR9mxJUvz-RSjCSakhTCatma28wponDmu_Sa61ayYfB8-IGoDACdg09LHTl-pGd0A92kcuEe7v3SFB2GMd2GJmfBVDxIX-vf_lB8dl26itO2m5KxVyurFeccF-LyEAjdJhd5_gOhU--0D5TOnvm6RQNX0wNEmwvwt4anT9EJReP8u-pfaHiZx3osEOy6aSxXab_h7Fu2w0IhcENhIEqC' },
      { name: 'Yogurt', description: 'Happy tummy!', image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBCPNSdS-WJ8Ix7CwX_1LwtJamOSa1fVzbdfk8KPp4llNl6lZDlTPiFV0XcTS03vGPhacmMdlQUXdz6OzRypAIxX4t0TuxBwMUyYcTWqNO1-j-R13OC127j1wi81Xxb22UXReHmlmGgQ1-84cmYcFbYo6QRKZZiT8HOUMwyZ5h0C0sHGlZySQjI91Hk-YKLBRw5EVhyfYkpNOKv2DIBuZH0nZ2qaA9obP67iEYrhm3phN48slnoCogUFTRBXtLf-kJ_WgtMoxqIf0pK' },
      { name: 'Whole Wheat Bread', description: 'Steady energy!', image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCt05NICLQgdRFnZ8BA77Hg3WPlw2i_CSA9Giiu2fV3mBULEjEi9PZ98oLbfyHHC5dmM5BKspL7kiObl8pTBPuCN36UK1_36Ff4HSMSNQgqXcVWwCB1ZvUkawYsk7E5GcMTFc9rJmY_SuxZcunSc1j8QYjegqJ8bRH1wU8-qo8ywz9c4CkoM4-lHEc2LmyIYQc1QlPLyAOBWP9cU_pKqIIq0ooxQ0EjRDUUjZtHfCzgyKyC7Qul-rGFq4tsViK7vciG6JEjQCawx7rR' }
    ],
    tryLess: {
      name: 'Donuts',
      image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBsJiDMxFbofpqv3TBCxNW2U0vuJ25JotMVuE4J_KJ-l8QwQzZsUeQq7k7OW6O84PReChBqmfEDCtIYE23nwRgo6vFf2aAD06PPrn9wwypxmiNr_ZtwLHcRDngW6VPW0PznMGA-KYy13k6QkUm5hJm7lrygySX8LqB0ulxquVks7o1e9t9t4zU_OiwkJYwNLeC-Xk1RWxdxYQNmrsNiZNrOKK_v32vefeagRPD8Nlub3FTkbp6pQGcS94OI9NBnKVRWOakBzwILSviN',
      alternative: {
        name: 'Banana',
        image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBrJkclsYpDmz3-b1gZiSIRbPkPZi79PP7NVytOwnp1wHtYjmCFItK2e5L9iR9mxJUvz-RSjCSakhTCatma28wponDmu_Sa61ayYfB8-IGoDACdg09LHTl-pGd0A92kcuEe7v3SFB2GMd2GJmfBVDxIX-vf_lB8dl26itO2m5KxVyurFeccF-LyEAjdJhd5_gOhU--0D5TOnvm6RQNX0wNEmwvwt4anT9EJReP8u-pfaHiZx3osEOy6aSxXab_h7Fu2w0IhcENhIEqC',
        tip: 'A banana gives you happy energy without the sugar crash! 🍌'
      }
    }
  },
  {
    id: 'strong',
    title: 'MUSCLE MAGIC',
    subtitle: 'Hero Strength!',
    icon: Dumbbell,
    gradient: ['#2563eb', '#312e81'],
    tilt: 'right',
    bgIcon: 'fitness_center',
    description: 'Charge up your muscles with these mighty power snacks! 💪🦸',
    mascotTip: 'Protein power for your growing muscles!',
    superFoods: [
      { name: 'Eggs', description: 'Protein power!', image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuAZGcFl9Ii8gVLiu7SNhOUrn0VVRO9yQBsMLySaxxi7BkiueRjuhqoS0rg4swPkHzFrEijQnkxCnt_3d5pMxWd8Ky7vyYNXpshJ3hpQ_lhWXu5GMyLb-_4LxyH-D7DX6ywAeVAdyFGu0SXjLMDkknw83sgUQe9DorWv0IwlmKecaWIqPGClmsNGQl9IlYayHVoNBSRS81spV75_AE765QCHE12qJjs_3QdO7P6CgqgB2ACKI27vnHW4fabgoasD3TifKO_5BjYF' },
      { name: 'Milk', description: 'Muscle fuel!', image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuByMR_KXYExPqayGjFnbQs9l7_kcEqWPikTaAZdb3GaMuzIWAPXB0n9Gm76rbuYQrbCQpbz2H1TGD8mwsMqGRGuPdA9xwLbsOjmE_tLqnn50aeV_mKnHoueIkrQBjupfHR8diOZ-fwMVuCekv3wkR0MCJZ2s_ykXshKExncGd44jkbx8jJwwWf_MgbXAtlfymresZ7O0hxHP8qFDAJlhCkiFZTzQLxlNH1o8_m11NymQFQ2FxqWe86K-q8AqMuDrAzNlW44mi16' },
      { name: 'Grilled Chicken', description: 'Strong muscles!', image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBntfbW5joP_xgCFcmrhos2RnhIj8SOBZYPlkKBbAgPmSyyCx79gXtJhgiOl-h5BZQCSM_cE1ZWdTPr_ysm56LT3n09KWo2xyxqlyf2rZsbfbUZa9rQcbXAYZrggRNa2nKE7awRr4B_nU78XTELskPJ35pKXLGYOzMDQU4C8nfxVdYHvMq0TxuKTj4ovH9gYDeskItz4Ukjj43U81OlAbVSbU-MJUnmG51rwAOD7pY5nY48veuNt-JLHrkRbbFkQYCo2t0ffWbT' }
    ],
    tryLess: {
      name: 'Fries',
      image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBNzfr0dzJRP35NfxPj_0-lZHAubIcO4cqtA4Does8ayQ5xEOptGXY4Pw70gJp5PaXrKc1KYbtfjpH6AGrhcHe2ff6lJMMz_PpZyU3wHRYf3uAsQ-zXh7BVvmfo5fTMTVAQH_agEM6RJ_aFL-yuSX3UYZmxSLNgQa5R7pyBiNd-q1HnzUyOS8khj-O6tb-DczyQb-OAgHp0Rv2A7vMTyawbK8GDBLsNOLsJJ7lDEtwKoTgzy5-d7DS1n1th8Txie6jdZUKx0It6',
      alternative: {
        name: 'Sandwich',
        image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCiCqHSGN4DCdOnqXmhS5MITy3jcNYz4yL-fC6RcP5qhK69CtY-s22C3RZ1jWhqs7lvKZkCFmC4Hnbz8UhpFt3RalOay0jj6R4ZJEY4hbOcJEXBoGwSbGh40jFO_WtezBm7uAJtJbPSBIcC8ExGqnvafNSNhhqICtJh1rUqv-J6oplfzFb34otIXYrc399v0uaE5zrgQ9-jmB9tqsGsJtFlYXerBFXEfnN1tBwIXXMLMz29amJljNcCEHtBNrLXMvhB60TH781l',
        tip: 'Wow! Swapping fries for a yummy sandwich gives you hero-strength energy! 🚀'
      }
    }
  }
];

export default function GoalScreen() {
  const [selectedGoalId, setSelectedGoalId] = useState<string | null>(null);
  const [recommendations, setRecommendations] = useState<RecommendationResponse | null>(null);
  const [recLoading, setRecLoading] = useState(false);

  const selectedGoal = GOALS.find(g => g.id === selectedGoalId);

  useEffect(() => {
    if (!selectedGoalId) {
      setRecommendations(null);
      return;
    }

    let cancelled = false;

    const fetchRecs = async () => {
      setRecLoading(true);
      setRecommendations(null);
      try {
        const profile = await getUserProfile();
        const prefs = profile?.foodPreferences;

        const data = await getRecommendations(
          selectedGoalId,
          prefs?.likes ?? [],
          prefs?.dislikes ?? [],
          prefs?.blacklist ?? []
        );

        if (!cancelled) setRecommendations(data);
      } catch {
        // API failed: keep recommendations null so components fall back to static GOALS data
        if (!cancelled) setRecommendations(null);
      } finally {
        if (!cancelled) setRecLoading(false);
      }
    };

    fetchRecs();
    return () => { cancelled = true; };
  }, [selectedGoalId]);

  const renderGoalList = () => (
    <ScrollView style={styles.scrollView} showsVerticalScrollIndicator={false}>
      {/* Hero Section */}
      <View style={styles.heroSection}>
        <Text style={styles.heroTitle}>Goals</Text>
        <Text style={styles.heroSubtitle}>
          Pick a path and complete daily quests to earn hero badges.
        </Text>
      </View>

      {/* Goals Grid */}
      <View style={styles.grid}>
        {GOALS.map((goal, index) => (
          <TouchableOpacity
            key={goal.id}
            style={[
              styles.goalCard,
              {
                transform: [{ rotate: `${index % 2 === 0 ? -2 : 2}deg` }],
              },
            ]}
            activeOpacity={0.9}
            onPress={() => setSelectedGoalId(goal.id)}
          >
            <View
              style={[
                styles.goalCardContent,
                {
                  backgroundColor: goal.gradient[0],
                },
              ]}
            >
              {/* Background Icon */}
              <View style={styles.bgIconContainer}>
                <goal.icon size={120} color="#ffffff" strokeWidth={1} />
              </View>

              {/* Content */}
              <View style={styles.cardContent}>
                <View style={[styles.iconCircle, { backgroundColor: 'rgba(255,255,255,0.2)' }]}>
                  <goal.icon size={40} color="#ffffff" />
                </View>
                <Text style={styles.cardTitle}>{goal.title}</Text>
                <Text style={styles.cardSubtitle}>{goal.subtitle}</Text>
              </View>
            </View>
          </TouchableOpacity>
        ))}
      </View>
    </ScrollView>
  );

  const renderGoalDetail = () => {
    if (!selectedGoal) return null;

    const detailProps = {
      onBack: () => setSelectedGoalId(null),
      recommendations,
      recLoading,
    };

    switch (selectedGoal.id) {
      case 'grow':
        return <GrowUpDetail goal={selectedGoal} {...detailProps} />;
      case 'see':
        return <SeeClearDetail goal={selectedGoal} {...detailProps} />;
      case 'think':
        return <ThinkFastDetail goal={selectedGoal} {...detailProps} />;
      case 'fight':
        return <FightGermsDetail goal={selectedGoal} {...detailProps} />;
      case 'feel':
        return <FeelGoodDetail goal={selectedGoal} {...detailProps} />;
      case 'strong':
        return <BeStrongDetail goal={selectedGoal} {...detailProps} />;
      default:
        return (
          <View style={styles.detailFallback}>
            <Text style={styles.detailTitle}>{selectedGoal.title}</Text>
            <Text style={styles.detailDescription}>{selectedGoal.description}</Text>
            <TouchableOpacity
              style={styles.backButton}
              onPress={() => setSelectedGoalId(null)}
            >
              <Text style={styles.backButtonText}>Go Back</Text>
            </TouchableOpacity>
          </View>
        );
    }
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.container}>
        {/* Shared app header with menu button */}
        <AppHeader title={selectedGoalId ? selectedGoal?.title : 'NutriHeroes'} />

        {/* Content */}
        {selectedGoalId ? renderGoalDetail() : renderGoalList()}

      </ScrollView>
      
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#F6F8EC',
  },
  container: {
    flex: 1,
    paddingHorizontal: 20,
    paddingTop: 8,
    backgroundColor: '#F8F5E9',
  },
  scrollView: {
    flex: 1,
  },
  heroSection: {
    alignItems: 'center',
    paddingVertical: 24,
    paddingHorizontal: 24,
  },
  heroTitle: {
    fontSize: 36,
    fontWeight: '900',
    color: '#B45309',
    marginBottom: 8,
  },
  heroSubtitle: {
    fontSize: 15,
    lineHeight: 22,
    color: '#666',
    textAlign: 'center',
    maxWidth: 280,
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: 24,
    paddingHorizontal: 24,
    paddingBottom: 32,
  },
  goalCard: {
    width: CARD_WIDTH,
    height: 220,
  },
  goalCardContent: {
    flex: 1,
    borderRadius: 16,
    overflow: 'hidden',
    position: 'relative',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
  bgIconContainer: {
    position: 'absolute',
    top: -16,
    right: -16,
    opacity: 0.1,
    transform: [{ rotate: '12deg' }],
  },
  cardContent: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 20,
  },
  iconCircle: {
    width: 80,
    height: 80,
    borderRadius: 40,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: '900',
    color: '#ffffff',
    textTransform: 'uppercase',
    letterSpacing: 1,
    textAlign: 'center',
  },
  cardSubtitle: {
    fontSize: 10,
    fontWeight: '700',
    color: 'rgba(255,255,255,0.9)',
    textTransform: 'uppercase',
    letterSpacing: 2,
    marginTop: 4,
    textAlign: 'center',
  },
  detailFallback: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
  },
  detailTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 16,
    color: '#333',
  },
  detailDescription: {
    fontSize: 16,
    color: '#666',
    textAlign: 'center',
    lineHeight: 24,
  },
  backButton: {
    marginTop: 32,
    backgroundColor: '#1E90FF',
    paddingHorizontal: 32,
    paddingVertical: 12,
    borderRadius: 24,
  },
  backButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: 'bold',
  },
});
